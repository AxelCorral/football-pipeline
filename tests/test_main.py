"""Tests unitaires pour src/main.py (orchestration run_pipeline)."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.config import Config
from src.main import COMPETITIONS, run_pipeline


@pytest.fixture
def config() -> Config:
    return Config(
        api_key="test-api-key",
        aws_bucket_name="test-bucket",
        aws_region="eu-west-1",
    )


def _raw_df(n: int) -> pd.DataFrame:
    """DataFrame brut minimal — suffisant pour traverser transform()."""
    return pd.DataFrame({"id": range(n)}) if n else pd.DataFrame()


class TestRunPipeline:
    @pytest.mark.parametrize("bucket_name", ["", " \n "])
    def test_missing_bucket_returns_empty_without_calling_api(self, bucket_name):
        cfg = Config(api_key="k", aws_bucket_name=bucket_name)
        with patch("src.main.fetch_all_competitions") as mock_fetch:
            result = run_pipeline(cfg)
        assert result == {}
        mock_fetch.assert_not_called()

    @patch("src.main.save_as_parquet")
    @patch("src.main.transform")
    @patch("src.main.load_raw_from_s3")
    @patch("src.main.upload_to_s3")
    @patch("src.main.fetch_all_competitions")
    def test_all_competitions_succeed(
        self, mock_fetch, mock_upload, mock_load, mock_transform, mock_save, config
    ):
        mock_fetch.return_value = {code: [{"id": 1}] for code in COMPETITIONS}
        mock_load.return_value = _raw_df(1)
        mock_transform.return_value = pd.DataFrame(
            {"season": [2025], "home_team": ["A"], "away_team": ["B"]}
        )

        result = run_pipeline(config)

        assert result == {code: 1 for code in COMPETITIONS}
        assert mock_upload.call_count == len(COMPETITIONS)
        assert mock_save.call_count == len(COMPETITIONS)

    @patch("src.main.save_as_parquet")
    @patch("src.main.transform")
    @patch("src.main.load_raw_from_s3")
    @patch("src.main.upload_to_s3")
    @patch("src.main.fetch_all_competitions")
    def test_competition_with_no_matches_is_skipped(
        self, mock_fetch, mock_upload, mock_load, mock_transform, mock_save, config
    ):
        mock_fetch.return_value = {
            code: [] if code == "PL" else [{"id": 1}] for code in COMPETITIONS
        }
        mock_load.return_value = _raw_df(1)
        mock_transform.return_value = pd.DataFrame(
            {"season": [2025], "home_team": ["A"], "away_team": ["B"]}
        )

        result = run_pipeline(config)

        assert result["PL"] == 0
        mock_upload.assert_any_call([{"id": 1}], "test-bucket", "FL1", config=config)
        # PL n'a jamais atteint upload_to_s3
        called_codes = [c.args[2] for c in mock_upload.call_args_list]
        assert "PL" not in called_codes

    @patch("src.main.save_as_parquet")
    @patch("src.main.transform")
    @patch("src.main.load_raw_from_s3")
    @patch("src.main.upload_to_s3")
    @patch("src.main.fetch_all_competitions")
    def test_competition_failure_does_not_stop_following_competitions(
        self, mock_fetch, mock_upload, mock_load, mock_transform, mock_save, config
    ):
        mock_fetch.return_value = {code: [{"id": 1}] for code in COMPETITIONS}
        mock_upload.side_effect = [
            RuntimeError("S3 unavailable"),
            None,
            None,
            None,
            None,
        ]
        mock_load.return_value = _raw_df(1)
        mock_transform.return_value = pd.DataFrame(
            {"season": [2025], "home_team": ["A"], "away_team": ["B"]}
        )

        result = run_pipeline(config)

        assert result["PL"] == 0
        assert result["FL1"] == 1
        assert mock_upload.call_count == len(COMPETITIONS)
        assert mock_save.call_count == len(COMPETITIONS) - 1

    @patch("src.main.save_as_parquet")
    @patch("src.main.transform")
    @patch("src.main.load_raw_from_s3")
    @patch("src.main.upload_to_s3")
    @patch("src.main.fetch_all_competitions")
    def test_empty_s3_reread_is_skipped(
        self, mock_fetch, mock_upload, mock_load, mock_transform, mock_save, config
    ):
        mock_fetch.return_value = {code: [{"id": 1}] for code in COMPETITIONS}
        mock_load.return_value = pd.DataFrame()  # relecture S3 vide

        result = run_pipeline(config)

        assert result == {code: 0 for code in COMPETITIONS}
        mock_transform.assert_not_called()
        mock_save.assert_not_called()

    @patch("src.main.save_as_parquet")
    @patch("src.main.transform")
    @patch("src.main.load_raw_from_s3")
    @patch("src.main.upload_to_s3")
    @patch("src.main.fetch_all_competitions")
    def test_falls_back_to_current_year_when_season_missing(
        self, mock_fetch, mock_upload, mock_load, mock_transform, mock_save, config
    ):
        from datetime import date

        mock_fetch.return_value = {"PL": [{"id": 1}]}
        mock_load.return_value = _raw_df(1)
        mock_transform.return_value = pd.DataFrame(
            {"season": [pd.NA], "home_team": ["A"], "away_team": ["B"]}
        )

        with patch("src.main.COMPETITIONS", ["PL"]):
            run_pipeline(config)

        key_arg = mock_save.call_args.args[2]
        assert str(date.today().year) in key_arg

    @patch("src.main.save_as_parquet")
    @patch("src.main.transform")
    @patch("src.main.load_raw_from_s3")
    @patch("src.main.upload_to_s3")
    @patch("src.main.fetch_all_competitions")
    def test_keeps_only_latest_available_season(
        self, mock_fetch, mock_upload, mock_load, mock_transform, mock_save, config
    ):
        mock_fetch.return_value = {"PL": [{"id": 1}]}
        mock_load.return_value = _raw_df(3)
        mock_transform.return_value = pd.DataFrame(
            {
                "season": [2024, 2025, 2025],
                "home_team": ["A", "B", "C"],
                "away_team": ["D", "E", "F"],
            }
        )

        with patch("src.main.COMPETITIONS", ["PL"]):
            result = run_pipeline(config)

        saved_df = mock_save.call_args.args[0]
        assert saved_df["season"].tolist() == [2025, 2025]
        assert mock_save.call_args.args[2] == "curated/PL/2025/matches.parquet"
        assert result == {"PL": 2}
