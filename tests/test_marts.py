"""Tests pour src/marts.py et scripts/export_marts.py.

La seconde moitié du fichier teste l'export versionné dans data/marts/ comme un
contrat : c'est ce que le dashboard déployé et l'entraînement lisent, et une
colonne renommée en amont doit échouer ici plutôt qu'en production.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from src.marts import (  # noqa: E402
    EXPORTED,
    FCT_MATCH_FEATURES,
    MART_LEAGUE_OVERVIEW,
    MART_MATCHWEEK_GOALS,
    MART_TEAM_FORM,
    mart_path,
    read_mart,
)
from src.ml.features import FEATURE_SOURCE  # noqa: E402

import export_marts  # noqa: E402  (scripts/ ajouté au path ci-dessus)

MARTS_DIR = ROOT / "data" / "marts"
marts_exported = pytest.mark.skipif(
    not (MARTS_DIR / f"{FCT_MATCH_FEATURES}.parquet").exists(),
    reason="marts non exportés — lancer dbt build puis scripts/export_marts.py",
)


# ---------------------------------------------------------------------------
# src/marts.py
# ---------------------------------------------------------------------------


class TestMartPaths:
    def test_path_is_parquet_under_the_marts_dir(self):
        assert mart_path(FCT_MATCH_FEATURES, "x").as_posix() == (
            f"x/{FCT_MATCH_FEATURES}.parquet"
        )

    def test_missing_mart_explains_how_to_produce_it(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="export_marts"):
            read_mart(FCT_MATCH_FEATURES, tmp_path)

    def test_reads_an_exported_parquet(self, tmp_path):
        frame = pd.DataFrame({"a": [1, 2]})
        frame.to_parquet(mart_path("demo", tmp_path), index=False)
        pd.testing.assert_frame_equal(read_mart("demo", tmp_path), frame)

    def test_exported_list_matches_the_named_marts(self):
        assert set(EXPORTED) == {
            FCT_MATCH_FEATURES,
            MART_TEAM_FORM,
            MART_LEAGUE_OVERVIEW,
            MART_MATCHWEEK_GOALS,
        }


# ---------------------------------------------------------------------------
# scripts/export_marts.py
# ---------------------------------------------------------------------------


@pytest.fixture
def duckdb_warehouse(tmp_path):
    """Un entrepôt DuckDB minimal contenant les quatre marts."""
    duckdb = pytest.importorskip("duckdb")
    path = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(path)) as con:
        for model in EXPORTED:
            con.execute(
                f'create table main."{model}" as '
                "select * from (values (1, 'a'), (2, 'b')) as t(id, label)"
            )
    return path


class TestExportFromDuckdb:
    def test_writes_one_parquet_per_mart(self, duckdb_warehouse, tmp_path):
        out = tmp_path / "marts"
        written = export_marts.export(
            "duckdb", marts_dir=out, duckdb_path=duckdb_warehouse
        )
        assert set(written) == set(EXPORTED)
        for model in EXPORTED:
            assert mart_path(model, out).exists()
            assert len(read_mart(model, out)) == 2

    def test_missing_warehouse_points_at_dbt_build(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="dbt build"):
            export_marts.export(
                "duckdb", marts_dir=tmp_path, duckdb_path=tmp_path / "absent.duckdb"
            )

    def test_empty_mart_aborts_instead_of_overwriting(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            export_marts, "read_from_duckdb", lambda *a, **k: pd.DataFrame()
        )
        with pytest.raises(RuntimeError, match="vide"):
            export_marts.export("duckdb", marts_dir=tmp_path)


# ---------------------------------------------------------------------------
# Le contrat de l'export versionné
# ---------------------------------------------------------------------------


@marts_exported
class TestExportedContract:
    def test_every_mart_is_present_and_non_empty(self):
        for model in EXPORTED:
            assert not read_mart(model, MARTS_DIR).empty

    def test_feature_columns_expected_by_the_models_exist(self):
        mart = read_mart(FCT_MATCH_FEATURES, MARTS_DIR)
        for column in FEATURE_SOURCE.values():
            assert column in mart.columns

    def test_one_row_per_match(self):
        mart = read_mart(FCT_MATCH_FEATURES, MARTS_DIR)
        assert mart["match_id"].is_unique
        assert mart["match_id"].notna().all()

    def test_target_stays_in_its_domain(self):
        mart = read_mart(FCT_MATCH_FEATURES, MARTS_DIR)
        assert set(mart["target_result"].dropna()) <= {"H", "D", "A"}

    def test_a_played_match_always_carries_a_target(self):
        mart = read_mart(FCT_MATCH_FEATURES, MARTS_DIR)
        assert mart.loc[mart["is_played"], "target_result"].notna().all()

    def test_no_feature_is_built_on_the_match_itself_or_later(self):
        """La forme retenue doit dater d'avant le coup d'envoi, des deux côtés."""
        mart = read_mart(FCT_MATCH_FEATURES, MARTS_DIR)
        for side in ("home", "away"):
            known = mart[mart[f"{side}_form_as_of"].notna()]
            assert (known[f"{side}_form_as_of"] < known["match_date"]).all()

    def test_a_side_without_history_has_no_features(self):
        mart = read_mart(FCT_MATCH_FEATURES, MARTS_DIR)
        blank = mart[mart["home_home_matches_played"] == 0]
        assert blank["home_home_avg_points_last_5"].isna().all()

    def test_team_form_has_one_row_per_team_and_season(self):
        form = read_mart(MART_TEAM_FORM, MARTS_DIR)
        assert not form.duplicated(["team", "competition_code", "season"]).any()

    def test_league_overview_results_add_up(self):
        overview = read_mart(MART_LEAGUE_OVERVIEW, MARTS_DIR)
        total = overview["home_wins"] + overview["draws"] + overview["away_wins"]
        assert (total == overview["matches_played"]).all()

    def test_league_overview_covers_every_match_of_the_feature_mart(self):
        mart = read_mart(FCT_MATCH_FEATURES, MARTS_DIR)
        overview = read_mart(MART_LEAGUE_OVERVIEW, MARTS_DIR)
        assert int(overview["matches_played"].sum()) == int(mart["is_played"].sum())

    def test_matchweeks_are_mondays(self):
        weeks = read_mart(MART_MATCHWEEK_GOALS, MARTS_DIR)
        assert (pd.to_datetime(weeks["matchweek_start"]).dt.weekday == 0).all()
