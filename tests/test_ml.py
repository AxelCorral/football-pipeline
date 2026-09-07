"""Tests unitaires pour le module src/ml/.

Les features ne sont plus calculées en Python : ces tests portent donc sur la
lecture du mart dbt, sur la traduction mart → matrice modèle, et sur
l'entraînement. La justesse des fenêtres glissantes, elle, est testée là où
elles sont écrites — voir dbt/tests/ et tests/test_marts.py.
"""

import numpy as np
import pandas as pd
import pytest

from src.ml.evaluate import baseline_accuracy, brier_score, log_loss_score
from src.ml.features import (
    FEATURE_COLS,
    FEATURE_SOURCE,
    add_feature_columns,
    fixture_features,
    load_match_features,
    load_team_form,
    training_frame,
)
from src.ml.train import LABEL_MAP, train_model, train_model_with_metrics

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _mart_row(match_id, date, competition, home, away, result, *, history=5):
    """Une ligne de fct_match_features, avec un historique complet par défaut."""
    row = {
        "match_id": match_id,
        "match_date": pd.Timestamp(date),
        "competition_code": competition,
        "competition_name": competition,
        "season": 2025,
        "status": "FINISHED" if result else "SCHEDULED",
        "is_played": result is not None,
        "home_team": home,
        "away_team": away,
        "home_matches_played": history,
        "away_matches_played": history,
        "home_home_matches_played": history,
        "away_away_matches_played": history,
        "target_result": result,
    }
    # Des valeurs plausibles et séparables : le receveur va mieux quand il gagne.
    strong = result == "H"
    for column in FEATURE_SOURCE.values():
        if history == 0:
            row[column] = None
        elif column.startswith("home_home_avg_points"):
            row[column] = 2.4 if strong else 0.6
        elif column.startswith("away_away_avg_points"):
            row[column] = 0.6 if strong else 2.4
        elif "goals_for" in column:
            row[column] = 2.0 if strong else 0.8
        else:
            row[column] = 0.8 if strong else 2.0
    return row


@pytest.fixture
def mart() -> pd.DataFrame:
    """Un mart minimal : 20 matchs joués, 2 sans historique, 1 non joué."""
    rows = []
    for i in range(20):
        result = "H" if i % 3 == 0 else ("A" if i % 3 == 1 else "D")
        rows.append(
            _mart_row(
                1000 + i,
                f"2025-09-{i + 1:02d}",
                "PL" if i % 2 == 0 else "SA",
                f"home{i}",
                f"away{i}",
                result,
            )
        )
    rows.append(_mart_row(2000, "2025-08-01", "PL", "newA", "newB", "H", history=0))
    rows.append(_mart_row(2001, "2025-08-02", "SA", "newC", "newD", "D", history=0))
    rows.append(_mart_row(3000, "2025-12-01", "PL", "home0", "away1", None))
    return pd.DataFrame(rows)


@pytest.fixture
def team_form() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "team": "Alpha",
                "competition_code": "PL",
                "home_form_avg_points": 2.2,
                "home_form_avg_goals_for": 2.0,
                "home_form_avg_goals_against": 0.8,
                "away_form_avg_points": 1.0,
                "away_form_avg_goals_for": 1.2,
                "away_form_avg_goals_against": 1.6,
            },
            {
                "team": "Beta",
                "competition_code": "PL",
                "home_form_avg_points": 1.4,
                "home_form_avg_goals_for": 1.1,
                "home_form_avg_goals_against": 1.2,
                "away_form_avg_points": 0.4,
                "away_form_avg_goals_for": 0.6,
                "away_form_avg_goals_against": 2.2,
            },
            {
                "team": "Promu",
                "competition_code": "PL",
                "home_form_avg_points": None,
                "home_form_avg_goals_for": None,
                "home_form_avg_goals_against": None,
                "away_form_avg_points": None,
                "away_form_avg_goals_for": None,
                "away_form_avg_goals_against": None,
            },
        ]
    )


@pytest.fixture
def trainable(mart) -> pd.DataFrame:
    return training_frame(mart)


# ---------------------------------------------------------------------------
# Chargement du mart
# ---------------------------------------------------------------------------


class TestLoadMart:
    def test_missing_mart_names_the_command_to_run(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="export_marts"):
            load_match_features(tmp_path)

    def test_missing_team_form_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="export_marts"):
            load_team_form(tmp_path)

    def test_reads_and_sorts_by_kickoff(self, mart, tmp_path):
        (tmp_path / "fct_match_features.parquet").write_bytes(b"")
        mart.to_parquet(tmp_path / "fct_match_features.parquet", index=False)
        loaded = load_match_features(tmp_path)
        assert loaded["match_date"].is_monotonic_increasing
        assert len(loaded) == len(mart)


# ---------------------------------------------------------------------------
# add_feature_columns / training_frame
# ---------------------------------------------------------------------------


class TestFeatureMatrix:
    def test_all_feature_columns_present(self, mart):
        out = add_feature_columns(mart)
        for col in FEATURE_COLS:
            assert col in out.columns

    def test_home_advantage_always_one(self, mart):
        assert (add_feature_columns(mart)["home_advantage"] == 1).all()

    def test_features_come_from_the_mart_untouched(self, mart):
        out = add_feature_columns(mart)
        for feature, source in FEATURE_SOURCE.items():
            expected = pd.to_numeric(mart[source], errors="coerce")
            pd.testing.assert_series_equal(
                out[feature], expected, check_names=False, check_dtype=False
            )

    def test_source_frame_is_not_mutated(self, mart):
        before = list(mart.columns)
        add_feature_columns(mart)
        assert list(mart.columns) == before

    def test_training_frame_drops_rows_without_target(self, mart):
        assert 3000 not in set(training_frame(mart)["match_id"])

    def test_training_frame_drops_rows_without_history(self, mart):
        """Un promu sans historique est écarté, jamais imputé à zéro."""
        kept = set(training_frame(mart)["match_id"])
        assert 2000 not in kept and 2001 not in kept

    def test_training_frame_filters_on_competition(self, mart):
        frame = training_frame(mart, competition_code="PL")
        assert set(frame["competition_code"]) == {"PL"}

    def test_training_frame_is_chronological(self, trainable):
        assert trainable["match_date"].is_monotonic_increasing

    def test_training_frame_ties_are_broken_by_match_id(self):
        """Deux coups d'envoi identiques doivent toujours sortir dans le même ordre."""
        rows = [
            _mart_row(20, "2025-09-06", "PL", "a", "b", "H"),
            _mart_row(10, "2025-09-06", "PL", "c", "d", "A"),
        ]
        frame = training_frame(pd.DataFrame(rows))
        assert frame["match_id"].tolist() == [10, 20]


# ---------------------------------------------------------------------------
# fixture_features
# ---------------------------------------------------------------------------


class TestFixtureFeatures:
    def test_returns_one_row_in_model_order(self, team_form):
        row = fixture_features(team_form, "Alpha", "Beta")
        assert list(row.columns) == FEATURE_COLS
        assert len(row) == 1

    def test_takes_home_form_of_home_side_and_away_form_of_away_side(self, team_form):
        row = fixture_features(team_form, "Alpha", "Beta").iloc[0]
        assert row["home_form"] == pytest.approx(2.2)
        assert row["away_form"] == pytest.approx(0.4)
        assert row["home_goals_avg"] == pytest.approx(2.0)
        assert row["away_conceded_avg"] == pytest.approx(2.2)

    def test_unknown_team_returns_none(self, team_form):
        assert fixture_features(team_form, "Alpha", "Inconnue") is None

    def test_team_without_form_returns_none(self, team_form):
        assert fixture_features(team_form, "Promu", "Beta") is None
        assert fixture_features(team_form, "Alpha", "Promu") is None


# ---------------------------------------------------------------------------
# train_model
# ---------------------------------------------------------------------------


class TestTrainModel:
    def test_returns_model_accuracy_cm(self, trainable, tmp_path):
        model, acc, cm = train_model(trainable, models_dir=tmp_path)
        assert model is not None
        assert 0.0 <= acc <= 1.0
        assert cm.shape == (3, 3)

    def test_model_file_saved(self, trainable, tmp_path):
        train_model(trainable, models_dir=tmp_path)
        assert len(list(tmp_path.glob("*.joblib"))) == 1

    def test_confusion_matrix_labels(self, trainable, tmp_path):
        """La matrice de confusion doit couvrir H=0, D=1, A=2."""
        _, _, cm = train_model(trainable, models_dir=tmp_path)
        assert cm.shape == (len(LABEL_MAP), len(LABEL_MAP))

    def test_metrics_variant_reports_probabilistic_scores(self, trainable, tmp_path):
        _model, metrics, _cm = train_model_with_metrics(trainable, models_dir=tmp_path)
        assert metrics["model"] in {"logistic_regression", "random_forest"}
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert metrics["log_loss"] > 0.0
        assert 0.0 <= metrics["brier"] <= 2.0
        assert metrics["n_train"] + metrics["n_test"] == len(trainable)

    def test_split_is_temporal_eighty_twenty(self, trainable, tmp_path):
        _model, metrics, _cm = train_model_with_metrics(trainable, models_dir=tmp_path)
        assert metrics["n_train"] == int(len(trainable) * 0.8)

    def test_raises_on_insufficient_data(self, tmp_path):
        tiny = pd.DataFrame(
            {
                **{col: [1.0] * 5 for col in FEATURE_COLS},
                "target_result": ["H", "D", "A", "H", "D"],
            }
        )
        with pytest.raises(ValueError, match="insuffisantes"):
            train_model(tiny, models_dir=tmp_path)

    def test_model_can_predict(self, trainable, tmp_path):
        model, _, _ = train_model(trainable, models_dir=tmp_path)
        assert hasattr(model, "predict")


# ---------------------------------------------------------------------------
# Métriques
# ---------------------------------------------------------------------------


class TestBaselineAccuracy:
    def test_returns_float(self, mart):
        assert isinstance(baseline_accuracy(mart), float)

    def test_between_zero_and_one(self, mart):
        assert 0.0 <= baseline_accuracy(mart) <= 1.0

    def test_ignores_matches_without_target(self, mart):
        played = mart[mart["target_result"].notna()]
        assert baseline_accuracy(mart) == pytest.approx(baseline_accuracy(played))

    def test_empty_dataframe_returns_zero(self):
        assert baseline_accuracy(pd.DataFrame(columns=["target_result"])) == 0.0

    def test_missing_column_returns_zero(self):
        assert baseline_accuracy(pd.DataFrame({"other": [1, 2]})) == 0.0

    def test_all_home_wins(self):
        df = pd.DataFrame({"target_result": ["H"] * 4})
        assert baseline_accuracy(df) == pytest.approx(1.0)

    def test_no_home_wins(self):
        df = pd.DataFrame({"target_result": ["A", "D", "A"]})
        assert baseline_accuracy(df) == pytest.approx(0.0)


class TestProbabilisticMetrics:
    def test_perfect_prediction_scores_zero_brier(self):
        y = np.array([0, 1, 2])
        proba = np.eye(3)
        assert brier_score(y, proba) == pytest.approx(0.0)

    def test_uniform_prediction_scores_ln_three(self):
        y = np.array([0, 1, 2])
        proba = np.full((3, 3), 1 / 3)
        assert log_loss_score(y, proba) == pytest.approx(np.log(3), abs=1e-6)

    def test_brier_penalises_confident_mistakes(self):
        y = np.array([0])
        confident_wrong = brier_score(y, np.array([[0.0, 1.0, 0.0]]))
        hesitant_wrong = brier_score(y, np.array([[0.4, 0.5, 0.1]]))
        assert confident_wrong > hesitant_wrong
