"""
Tests unitaires pour src/main.py (orchestrateur du pipeline ETL).

Couvre : mode --dry-run (aucun appel réseau/S3, config validée), orchestration
complète des 5 compétitions dans le bon ordre, filtre --competition, gestion
d'erreur (une compétition en échec n'interrompt pas les autres), parsing CLI.
Aucun appel réel : fetch/upload/transform/save sont entièrement mockés.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config import Config
from src.main import COMPETITION_NAMES, main, run_pipeline


def _curated_code(key: str) -> str:
    """Extrait le code compétition d'une clé curated/{code}/{season}/matches.parquet."""
    return key.split("/")[1]


class TestRunPipelineDryRun:
    """Mode --dry-run : aucun appel réseau/S3, juste une validation/affichage."""

    def test_no_network_or_s3_calls(self, mock_settings):
        """fetch/upload/load/transform/save ne doivent jamais être appelés."""
        with (
            patch("src.main.fetch_all_competitions") as mock_fetch,
            patch("src.main.upload_to_s3") as mock_upload,
            patch("src.main.load_raw_from_s3") as mock_load,
            patch("src.main.transform") as mock_transform,
            patch("src.main.save_as_parquet") as mock_save,
        ):
            run_pipeline(mock_settings, dry_run=True)

        mock_fetch.assert_not_called()
        mock_upload.assert_not_called()
        mock_load.assert_not_called()
        mock_transform.assert_not_called()
        mock_save.assert_not_called()

    def test_does_not_raise_with_incomplete_config(self):
        """Une config incomplète (bucket vide) ne doit pas lever en dry-run."""
        incomplete = Config(
            api_key="",
            aws_bucket_name="",
            aws_region="eu-west-1",
            athena_database="",
            athena_output_s3="",
        )

        with (
            patch("src.main.fetch_all_competitions"),
            patch("src.main.upload_to_s3"),
            patch("src.main.load_raw_from_s3"),
            patch("src.main.transform"),
            patch("src.main.save_as_parquet"),
        ):
            run_pipeline(incomplete, dry_run=True)  # ne doit pas lever

    def test_complete_config_passes_validation_too(self, mock_settings):
        """Une config complète doit aussi passer sans erreur en dry-run."""
        with (
            patch("src.main.fetch_all_competitions"),
            patch("src.main.upload_to_s3"),
            patch("src.main.load_raw_from_s3"),
            patch("src.main.transform"),
            patch("src.main.save_as_parquet"),
        ):
            run_pipeline(mock_settings, dry_run=True)  # ne doit pas lever

    def test_real_run_raises_without_bucket(self):
        """Hors dry-run, un bucket non configuré doit lever RuntimeError."""
        incomplete = Config(
            api_key="test-key",
            aws_bucket_name="",
            aws_region="eu-west-1",
            athena_database="",
            athena_output_s3="",
        )

        with pytest.raises(RuntimeError, match="AWS_BUCKET_NAME"):
            run_pipeline(incomplete, dry_run=False)


class TestRunPipelineOrchestration:
    """Mode normal : enchaînement fetch -> upload -> transform -> save."""

    def _setup_mocks(self, sample_matches: list[dict]):
        """Construit des mocks qui se propagent le code compétition entre étapes."""
        order: list[str] = []

        def _fetch_side_effect(competitions, season=None, *, config=None):
            return {code: sample_matches for code in competitions}

        def _upload_side_effect(data, bucket, code, run_date=None, *, config=None):
            order.append(f"upload:{code}")
            return f"s3://{bucket}/raw/{code}/.../matches.json"

        def _load_side_effect(bucket, code, *, config=None):
            order.append(f"load:{code}")
            return pd.DataFrame({"_code": [code]})

        def _transform_side_effect(df_raw):
            code = df_raw["_code"].iloc[0]
            order.append(f"transform:{code}")
            return pd.DataFrame({"season": [2023], "_code": [code]})

        def _save_side_effect(df, bucket, key, *, config=None):
            order.append(f"save:{_curated_code(key)}")
            return f"s3://{bucket}/{key}"

        mocks = {
            "fetch": MagicMock(side_effect=_fetch_side_effect),
            "upload": MagicMock(side_effect=_upload_side_effect),
            "load": MagicMock(side_effect=_load_side_effect),
            "transform": MagicMock(side_effect=_transform_side_effect),
            "save": MagicMock(side_effect=_save_side_effect),
        }
        return mocks, order

    def test_all_five_competitions_orchestrated_in_order(
        self, mock_settings, sample_raw_matches
    ):
        """Les 5 ligues doivent être traitées dans l'ordre, étape par étape."""
        mocks, order = self._setup_mocks(sample_raw_matches)

        with (
            patch("src.main.fetch_all_competitions", mocks["fetch"]),
            patch("src.main.upload_to_s3", mocks["upload"]),
            patch("src.main.load_raw_from_s3", mocks["load"]),
            patch("src.main.transform", mocks["transform"]),
            patch("src.main.save_as_parquet", mocks["save"]),
        ):
            run_pipeline(mock_settings)

        expected_codes = list(COMPETITION_NAMES)  # PL, FL1, BL1, SA, PD
        assert mocks["fetch"].call_args[0][0] == expected_codes

        expected_order = [
            step
            for code in expected_codes
            for step in (
                f"upload:{code}",
                f"load:{code}",
                f"transform:{code}",
                f"save:{code}",
            )
        ]
        assert order == expected_order

        assert mocks["upload"].call_count == 5
        assert mocks["load"].call_count == 5
        assert mocks["transform"].call_count == 5
        assert mocks["save"].call_count == 5

    def test_competition_filter_processes_only_requested_league(
        self, mock_settings, sample_raw_matches
    ):
        """competitions=["PL"] ne doit déclencher le pipeline que pour PL."""
        mocks, order = self._setup_mocks(sample_raw_matches)

        with (
            patch("src.main.fetch_all_competitions", mocks["fetch"]),
            patch("src.main.upload_to_s3", mocks["upload"]),
            patch("src.main.load_raw_from_s3", mocks["load"]),
            patch("src.main.transform", mocks["transform"]),
            patch("src.main.save_as_parquet", mocks["save"]),
        ):
            run_pipeline(mock_settings, ["PL"])

        assert mocks["fetch"].call_args[0][0] == ["PL"]
        assert mocks["upload"].call_count == 1
        assert mocks["load"].call_count == 1
        assert mocks["transform"].call_count == 1
        assert mocks["save"].call_count == 1
        assert order == ["upload:PL", "load:PL", "transform:PL", "save:PL"]

    def test_competition_with_no_matches_is_skipped(self, mock_settings):
        """Une compétition sans match (fetch vide) ne doit pas être traitée plus loin."""
        with (
            patch("src.main.fetch_all_competitions", return_value={"PL": []}),
            patch("src.main.upload_to_s3") as mock_upload,
            patch("src.main.load_raw_from_s3") as mock_load,
            patch("src.main.transform") as mock_transform,
            patch("src.main.save_as_parquet") as mock_save,
        ):
            run_pipeline(mock_settings, ["PL"])

        mock_upload.assert_not_called()
        mock_load.assert_not_called()
        mock_transform.assert_not_called()
        mock_save.assert_not_called()


class TestRunPipelineErrorHandling:
    """Une compétition en échec ne doit pas interrompre les autres."""

    def test_failure_on_one_competition_does_not_stop_the_others(
        self, mock_settings, sample_raw_matches
    ):
        """upload_to_s3 échoue pour BL1 : les 4 autres ligues doivent tout de même
        être sauvegardées, et run_pipeline ne doit pas lever."""
        codes = list(COMPETITION_NAMES)

        def _upload_side_effect(data, bucket, code, run_date=None, *, config=None):
            if code == "BL1":
                raise RuntimeError("S3 indisponible")
            return f"s3://{bucket}/raw/{code}/.../matches.json"

        def _load_side_effect(bucket, code, *, config=None):
            return pd.DataFrame({"_code": [code]})

        def _transform_side_effect(df_raw):
            code = df_raw["_code"].iloc[0]
            return pd.DataFrame({"season": [2023], "_code": [code]})

        saved_codes: list[str] = []

        def _save_side_effect(df, bucket, key, *, config=None):
            saved_codes.append(_curated_code(key))
            return f"s3://{bucket}/{key}"

        with (
            patch(
                "src.main.fetch_all_competitions",
                return_value={c: sample_raw_matches for c in codes},
            ),
            patch("src.main.upload_to_s3", side_effect=_upload_side_effect),
            patch("src.main.load_raw_from_s3", side_effect=_load_side_effect),
            patch("src.main.transform", side_effect=_transform_side_effect),
            patch(
                "src.main.save_as_parquet", side_effect=_save_side_effect
            ) as mock_save,
        ):
            run_pipeline(mock_settings)  # ne doit pas lever malgré l'échec BL1

        assert "BL1" not in saved_codes
        assert set(saved_codes) == set(codes) - {"BL1"}
        assert mock_save.call_count == 4

    def test_empty_transform_result_skips_save_but_continues(
        self, mock_settings, sample_raw_matches
    ):
        """transform() vide pour une ligue : save ignoré, les autres continuent."""
        codes = list(COMPETITION_NAMES)

        def _load_side_effect(bucket, code, *, config=None):
            return pd.DataFrame({"_code": [code]})

        def _transform_side_effect(df_raw):
            code = df_raw["_code"].iloc[0]
            if code == "SA":
                return pd.DataFrame()
            return pd.DataFrame({"season": [2023], "_code": [code]})

        saved_codes: list[str] = []

        def _save_side_effect(df, bucket, key, *, config=None):
            saved_codes.append(_curated_code(key))
            return f"s3://{bucket}/{key}"

        with (
            patch(
                "src.main.fetch_all_competitions",
                return_value={c: sample_raw_matches for c in codes},
            ),
            patch("src.main.upload_to_s3"),
            patch("src.main.load_raw_from_s3", side_effect=_load_side_effect),
            patch("src.main.transform", side_effect=_transform_side_effect),
            patch("src.main.save_as_parquet", side_effect=_save_side_effect),
        ):
            run_pipeline(mock_settings)

        assert "SA" not in saved_codes
        assert set(saved_codes) == set(codes) - {"SA"}


class TestMainCLI:
    """Parsing des arguments argparse (--competition, --season, --dry-run)."""

    def test_no_args_runs_all_competitions(self):
        with (
            patch("src.main.Config", return_value=MagicMock()),
            patch("src.main.run_pipeline") as mock_run,
        ):
            main([])

        args, kwargs = mock_run.call_args
        assert args[1] is None  # pas de filtre -> toutes les compétitions
        assert kwargs["season"] is None
        assert kwargs["dry_run"] is False

    def test_competition_flag_filters_to_one_league(self):
        with (
            patch("src.main.Config", return_value=MagicMock()),
            patch("src.main.run_pipeline") as mock_run,
        ):
            main(["--competition", "PL"])

        args, _ = mock_run.call_args
        assert args[1] == ["PL"]

    def test_season_flag_parsed_as_int(self):
        with (
            patch("src.main.Config", return_value=MagicMock()),
            patch("src.main.run_pipeline") as mock_run,
        ):
            main(["--season", "2024"])

        _, kwargs = mock_run.call_args
        assert kwargs["season"] == 2024

    def test_dry_run_flag_sets_dry_run_true(self):
        with (
            patch("src.main.Config", return_value=MagicMock()),
            patch("src.main.run_pipeline") as mock_run,
        ):
            main(["--dry-run"])

        _, kwargs = mock_run.call_args
        assert kwargs["dry_run"] is True

    def test_combined_flags(self):
        with (
            patch("src.main.Config", return_value=MagicMock()),
            patch("src.main.run_pipeline") as mock_run,
        ):
            main(["--competition", "SA", "--season", "2022", "--dry-run"])

        args, kwargs = mock_run.call_args
        assert args[1] == ["SA"]
        assert kwargs["season"] == 2022
        assert kwargs["dry_run"] is True

    def test_invalid_competition_choice_exits(self):
        with pytest.raises(SystemExit):
            main(["--competition", "XX"])
