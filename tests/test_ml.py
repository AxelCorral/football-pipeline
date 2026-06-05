"""Tests unitaires pour le module src/ml/."""

import pandas as pd
import pytest

from src.ml.evaluate import baseline_accuracy
from src.ml.features import FEATURE_COLS, compute_features
from src.ml.train import LABEL_MAP, train_model


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _match(date, home, away, hg, ag, status="FINISHED"):
    if status != "FINISHED":
        result = None
    elif hg > ag:
        result = "H"
    elif ag > hg:
        result = "A"
    else:
        result = "D"
    return {
        "date": pd.Timestamp(date, tz="UTC"),
        "home_team": home,
        "away_team": away,
        "home_goals": hg,
        "away_goals": ag,
        "result": result,
        "status": status,
    }


@pytest.fixture
def df_matches():
    """15 matchs FINISHED entre 3 équipes — assez pour des rolling stats."""
    rows = [
        _match("2024-01-01", "A", "B", 2, 0),
        _match("2024-01-08", "C", "A", 1, 1),
        _match("2024-01-15", "B", "C", 0, 2),
        _match("2024-01-22", "A", "C", 3, 1),
        _match("2024-01-29", "B", "A", 1, 0),
        _match("2024-02-05", "C", "B", 2, 2),
        _match("2024-02-12", "A", "B", 1, 1),
        _match("2024-02-19", "C", "A", 0, 1),
        _match("2024-02-26", "B", "C", 3, 0),
        _match("2024-03-04", "A", "C", 2, 0),
        _match("2024-03-11", "B", "A", 0, 0),
        _match("2024-03-18", "C", "B", 1, 2),
        _match("2024-03-25", "A", "B", 2, 1),
        _match("2024-04-01", "C", "A", 3, 2),
        _match("2024-04-08", "B", "C", 1, 1),
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def df_with_unfinished(df_matches):
    unfinished = pd.DataFrame([_match("2024-04-15", "A", "C", 0, 0, status="SCHEDULED")])
    return pd.concat([df_matches, unfinished], ignore_index=True)


@pytest.fixture
def df_features(df_matches):
    return compute_features(df_matches)


# ---------------------------------------------------------------------------
# compute_features
# ---------------------------------------------------------------------------


class TestComputeFeatures:
    def test_filters_to_finished_only(self, df_with_unfinished):
        result = compute_features(df_with_unfinished)
        assert (result["status"] == "FINISHED").all()

    def test_all_feature_columns_present(self, df_features):
        for col in FEATURE_COLS:
            assert col in df_features.columns

    def test_home_advantage_always_one(self, df_features):
        assert (df_features["home_advantage"] == 1).all()

    def test_sorted_by_date(self, df_features):
        dates = df_features["date"].tolist()
        assert dates == sorted(dates)

    def test_no_lookahead_first_home_match(self, df_matches):
        """Premier match à domicile d'une équipe → home_form NaN (pas d'historique)."""
        result = compute_features(df_matches)
        first_a = result[result["home_team"] == "A"].iloc[0]
        assert pd.isna(first_a["home_form"])

    def test_home_form_correct_after_two_wins(self, df_matches):
        """Équipe A : 2 victoires à domicile → 3e match doit afficher home_form=3.0."""
        result = compute_features(df_matches)
        # A joue à domicile : 01-jan (W), 22-jan (W), 12-fév → form = mean([3,3]) = 3.0
        third_a_home = result[result["home_team"] == "A"].iloc[2]
        assert third_a_home["home_form"] == pytest.approx(3.0)

    def test_no_private_columns_leaked(self, df_features):
        for col in df_features.columns:
            assert not col.startswith("_")

    def test_empty_input_returns_empty_with_columns(self):
        empty = pd.DataFrame(
            columns=["date", "home_team", "away_team", "home_goals", "away_goals", "result", "status"]
        )
        result = compute_features(empty)
        assert result.empty
        for col in FEATURE_COLS:
            assert col in result.columns


# ---------------------------------------------------------------------------
# train_model
# ---------------------------------------------------------------------------


class TestTrainModel:
    def test_returns_model_accuracy_cm(self, df_features, tmp_path):
        model, acc, cm = train_model(df_features, models_dir=tmp_path)
        assert model is not None
        assert 0.0 <= acc <= 1.0
        assert cm.shape == (3, 3)

    def test_model_file_saved(self, df_features, tmp_path):
        train_model(df_features, models_dir=tmp_path)
        assert len(list(tmp_path.glob("*.joblib"))) == 1

    def test_confusion_matrix_labels(self, df_features, tmp_path):
        """La matrice de confusion doit couvrir H=0, D=1, A=2."""
        _, _, cm = train_model(df_features, models_dir=tmp_path)
        assert cm.shape == (len(LABEL_MAP), len(LABEL_MAP))

    def test_raises_on_insufficient_data(self, tmp_path):
        tiny = pd.DataFrame(
            {
                "home_form": [1.0] * 5,
                "away_form": [1.0] * 5,
                "home_goals_avg": [1.0] * 5,
                "away_goals_avg": [1.0] * 5,
                "home_conceded_avg": [1.0] * 5,
                "away_conceded_avg": [1.0] * 5,
                "home_advantage": [1] * 5,
                "result": ["H", "D", "A", "H", "D"],
            }
        )
        with pytest.raises(ValueError, match="insuffisantes"):
            train_model(tiny, models_dir=tmp_path)

    def test_model_can_predict(self, df_features, tmp_path):
        model, _, _ = train_model(df_features, models_dir=tmp_path)
        assert hasattr(model, "predict")


# ---------------------------------------------------------------------------
# baseline_accuracy
# ---------------------------------------------------------------------------


class TestBaselineAccuracy:
    def test_returns_float(self, df_matches):
        assert isinstance(baseline_accuracy(df_matches), float)

    def test_between_zero_and_one(self, df_matches):
        acc = baseline_accuracy(df_matches)
        assert 0.0 <= acc <= 1.0

    def test_ignores_unfinished_matches(self, df_with_unfinished, df_matches):
        assert baseline_accuracy(df_with_unfinished) == pytest.approx(
            baseline_accuracy(df_matches)
        )

    def test_empty_dataframe_returns_zero(self):
        empty = pd.DataFrame(columns=["status", "result"])
        assert baseline_accuracy(empty) == 0.0

    def test_all_home_wins(self):
        df = pd.DataFrame({"status": ["FINISHED"] * 4, "result": ["H"] * 4})
        assert baseline_accuracy(df) == pytest.approx(1.0)

    def test_no_home_wins(self):
        df = pd.DataFrame({"status": ["FINISHED"] * 3, "result": ["A", "D", "A"]})
        assert baseline_accuracy(df) == pytest.approx(0.0)
