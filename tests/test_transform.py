"""
Tests unitaires pour src/transform/glue_transform.py
et src/transform/process_matches.py.

Aucun appel réel : boto3 est entièrement mocké.
"""

import io
import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config import Config
from src.transform.process_matches import (
    build_curated_key,
    load_raw_from_s3,
    save_as_parquet,
    transform,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> Config:
    return Config(
        api_key="test-key",
        aws_bucket_name="test-bucket",
        aws_region="eu-west-1",
        athena_database="test_db",
        athena_output_s3="s3://test-bucket/athena/",
        football_api_base_url="https://api.football-data.org/v4",
    )


@pytest.fixture
def raw_match() -> dict:
    """Match brut complet simulant la réponse de l'API football-data.org."""
    return {
        "id": 123456,
        "utcDate": "2024-03-15T20:00:00Z",
        "status": "FINISHED",
        "matchday": 29,
        "homeTeam": {"id": 65, "name": "Manchester City FC"},
        "awayTeam": {"id": 57, "name": "Arsenal FC"},
        "score": {
            "winner": "HOME_TEAM",
            "fullTime": {"home": 3, "away": 1},
        },
        "competition": {"id": 2021, "name": "Premier League", "code": "PL"},
        "season": {"id": 1490, "startDate": "2023-08-11"},
        "referees": [{"id": 11, "name": "Jon Moss", "type": "REFEREE"}],
        "venue": "Etihad Stadium",
    }


@pytest.fixture
def raw_df(raw_match) -> pd.DataFrame:
    """DataFrame normalisé simulant la sortie de load_raw_from_s3."""
    return pd.json_normalize([raw_match])


def _scheduled_match() -> dict:
    """Match non joué (score absent)."""
    return {
        "id": 999,
        "utcDate": "2024-05-01T15:00:00Z",
        "status": "SCHEDULED",
        "homeTeam": {"name": "Team A"},
        "awayTeam": {"name": "Team B"},
        "score": {"fullTime": {"home": None, "away": None}},
        "competition": {"name": "Premier League", "code": "PL"},
        "season": {"startDate": "2023-08-01"},
    }


def _mock_s3_with_content(pages: list[dict]) -> MagicMock:
    """Fabrique un mock S3 avec un paginateur retournant les pages données."""
    mock_s3 = MagicMock()
    paginator = MagicMock()
    mock_s3.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages
    return mock_s3


def _body(matches: list[dict]) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(matches).encode("utf-8")
    return body


# ---------------------------------------------------------------------------
# Tests existants (stubs GlueTransformer)
# ---------------------------------------------------------------------------


class TestGlueTransformer:
    """Tests du transformateur de données matchs (stubs)."""

    def test_transform_returns_dataframe(self, sample_raw_matches):
        pass

    def test_transform_flattens_nested_fields(self, sample_raw_matches):
        pass

    def test_transform_adds_partition_columns(self, sample_raw_matches):
        pass

    def test_transform_empty_input_returns_empty_dataframe(self):
        pass

    def test_flatten_match_extracts_team_names(self, sample_raw_matches):
        pass


# ---------------------------------------------------------------------------
# load_raw_from_s3
# ---------------------------------------------------------------------------


class TestLoadRawFromS3:
    """Tests de la fonction load_raw_from_s3."""

    def test_returns_dataframe_with_rows(self, config, raw_match):
        mock_s3 = _mock_s3_with_content(
            [{"Contents": [{"Key": "raw/PL/2024-03-15/matches.json"}]}]
        )
        mock_s3.get_object.return_value = {"Body": _body([raw_match])}

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            df = load_raw_from_s3("my-bucket", "PL", config=config)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_concatenates_multiple_files(self, config, raw_match):
        mock_s3 = _mock_s3_with_content(
            [
                {
                    "Contents": [
                        {"Key": "raw/PL/2024-03-15/matches.json"},
                        {"Key": "raw/PL/2024-03-16/matches.json"},
                    ]
                }
            ]
        )
        mock_s3.get_object.return_value = {"Body": _body([raw_match])}

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            df = load_raw_from_s3("my-bucket", "PL", config=config)

        assert len(df) == 2

    def test_ignores_non_json_files(self, config, raw_match):
        mock_s3 = _mock_s3_with_content(
            [
                {
                    "Contents": [
                        {"Key": "raw/PL/2024-03-15/matches.json"},
                        {"Key": "raw/PL/2024-03-15/meta.txt"},
                    ]
                }
            ]
        )
        mock_s3.get_object.return_value = {"Body": _body([raw_match])}

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            df = load_raw_from_s3("my-bucket", "PL", config=config)

        assert len(df) == 1
        assert mock_s3.get_object.call_count == 1

    def test_returns_empty_dataframe_when_prefix_empty(self, config):
        mock_s3 = _mock_s3_with_content([{}])  # pas de 'Contents'

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            df = load_raw_from_s3("my-bucket", "PL", config=config)

        assert df.empty

    def test_handles_multiple_pages(self, config, raw_match):
        mock_s3 = _mock_s3_with_content(
            [
                {"Contents": [{"Key": "raw/PL/2024-03-15/matches.json"}]},
                {"Contents": [{"Key": "raw/PL/2024-03-16/matches.json"}]},
            ]
        )
        mock_s3.get_object.return_value = {"Body": _body([raw_match])}

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            df = load_raw_from_s3("my-bucket", "PL", config=config)

        assert len(df) == 2

    def test_uses_region_from_config(self, config, raw_match):
        mock_s3 = _mock_s3_with_content(
            [{"Contents": [{"Key": "raw/PL/2024-03-15/matches.json"}]}]
        )
        mock_s3.get_object.return_value = {"Body": _body([raw_match])}

        with patch(
            "src.transform.process_matches.boto3.client", return_value=mock_s3
        ) as mock_client:
            load_raw_from_s3("my-bucket", "PL", config=config)

        mock_client.assert_called_once_with("s3", region_name="eu-west-1")


# ---------------------------------------------------------------------------
# transform
# ---------------------------------------------------------------------------


class TestTransform:
    """Tests de la fonction transform."""

    def test_returns_dataframe(self, raw_df):
        assert isinstance(transform(raw_df), pd.DataFrame)

    def test_output_has_all_expected_columns(self, raw_df):
        out = transform(raw_df)
        expected = {
            "match_id",
            "date",
            "competition",
            "competition_code",
            "season",
            "home_team",
            "away_team",
            "home_goals",
            "away_goals",
            "total_goals",
            "result",
            "status",
            "referee",
            "venue",
        }
        assert expected.issubset(set(out.columns))

    def test_extracts_match_id(self, raw_df):
        assert transform(raw_df)["match_id"].iloc[0] == 123456

    def test_date_is_timezone_aware_datetime(self, raw_df):
        out = transform(raw_df)
        assert pd.api.types.is_datetime64_any_dtype(out["date"])
        assert out["date"].dt.tz is not None

    def test_extracts_home_team(self, raw_df):
        assert transform(raw_df)["home_team"].iloc[0] == "Manchester City FC"

    def test_extracts_away_team(self, raw_df):
        assert transform(raw_df)["away_team"].iloc[0] == "Arsenal FC"

    def test_extracts_home_goals(self, raw_df):
        assert transform(raw_df)["home_goals"].iloc[0] == 3

    def test_extracts_away_goals(self, raw_df):
        assert transform(raw_df)["away_goals"].iloc[0] == 1

    def test_computes_total_goals(self, raw_df):
        assert transform(raw_df)["total_goals"].iloc[0] == 4

    def test_result_home_win(self, raw_df):
        assert transform(raw_df)["result"].iloc[0] == "H"

    def test_result_away_win(self):
        df = pd.json_normalize(
            [
                {
                    "id": 1,
                    "utcDate": "2024-01-01T00:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"name": "A"},
                    "awayTeam": {"name": "B"},
                    "score": {"fullTime": {"home": 0, "away": 2}},
                    "competition": {"name": "X", "code": "X"},
                    "season": {"startDate": "2023-08-01"},
                }
            ]
        )
        assert transform(df)["result"].iloc[0] == "A"

    def test_result_draw(self):
        df = pd.json_normalize(
            [
                {
                    "id": 1,
                    "utcDate": "2024-01-01T00:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"name": "A"},
                    "awayTeam": {"name": "B"},
                    "score": {"fullTime": {"home": 1, "away": 1}},
                    "competition": {"name": "X", "code": "X"},
                    "season": {"startDate": "2023-08-01"},
                }
            ]
        )
        assert transform(df)["result"].iloc[0] == "D"

    def test_result_is_none_when_score_absent(self):
        df = pd.json_normalize([_scheduled_match()])
        assert pd.isna(transform(df)["result"].iloc[0])

    def test_home_goals_none_when_not_played(self):
        df = pd.json_normalize([_scheduled_match()])
        assert pd.isna(transform(df)["home_goals"].iloc[0])

    def test_total_goals_none_when_score_absent(self):
        df = pd.json_normalize([_scheduled_match()])
        assert pd.isna(transform(df)["total_goals"].iloc[0])

    def test_goals_are_nullable_int(self, raw_df):
        out = transform(raw_df)
        assert str(out["home_goals"].dtype) == "Int64"
        assert str(out["away_goals"].dtype) == "Int64"
        assert str(out["total_goals"].dtype) == "Int64"

    def test_extracts_competition_name(self, raw_df):
        assert transform(raw_df)["competition"].iloc[0] == "Premier League"

    def test_extracts_competition_code(self, raw_df):
        assert transform(raw_df)["competition_code"].iloc[0] == "PL"

    def test_extracts_season_year(self, raw_df):
        assert transform(raw_df)["season"].iloc[0] == 2023

    def test_extracts_referee_first_in_list(self, raw_df):
        assert transform(raw_df)["referee"].iloc[0] == "Jon Moss"

    def test_referee_is_none_when_field_absent(self):
        df = pd.json_normalize(
            [
                {
                    "id": 1,
                    "utcDate": "2024-01-01T00:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"name": "A"},
                    "awayTeam": {"name": "B"},
                    "score": {"fullTime": {"home": 1, "away": 0}},
                    "competition": {"name": "X", "code": "X"},
                    "season": {"startDate": "2023-08-01"},
                }
            ]
        )
        assert pd.isna(transform(df)["referee"].iloc[0])

    def test_referee_is_none_when_list_is_empty(self):
        df = pd.json_normalize(
            [
                {
                    "id": 1,
                    "utcDate": "2024-01-01T00:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"name": "A"},
                    "awayTeam": {"name": "B"},
                    "score": {"fullTime": {"home": 1, "away": 0}},
                    "competition": {"name": "X", "code": "X"},
                    "season": {"startDate": "2023-08-01"},
                    "referees": [],
                }
            ]
        )
        assert transform(df)["referee"].iloc[0] is None

    def test_extracts_venue(self, raw_df):
        assert transform(raw_df)["venue"].iloc[0] == "Etihad Stadium"

    def test_venue_is_none_when_absent(self):
        df = pd.json_normalize(
            [
                {
                    "id": 1,
                    "utcDate": "2024-01-01T00:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"name": "A"},
                    "awayTeam": {"name": "B"},
                    "score": {"fullTime": {"home": 1, "away": 0}},
                    "competition": {"name": "X", "code": "X"},
                    "season": {"startDate": "2023-08-01"},
                }
            ]
        )
        assert pd.isna(transform(df)["venue"].iloc[0])

    def test_empty_dataframe_returns_column_schema(self):
        out = transform(pd.DataFrame())
        assert out.empty
        assert "match_id" in out.columns
        assert "result" in out.columns

    def test_multiple_matches_correct_row_count(self, raw_match):
        df = pd.json_normalize([raw_match, _scheduled_match()])
        out = transform(df)
        assert len(out) == 2

    def test_competition_code_none_when_field_absent(self):
        """competition.code absent de la réponse → colonne None, pas d'erreur."""
        df = pd.json_normalize(
            [
                {
                    "id": 1,
                    "utcDate": "2024-01-01T00:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"name": "A"},
                    "awayTeam": {"name": "B"},
                    "score": {"fullTime": {"home": 1, "away": 0}},
                    "competition": {"name": "League X"},  # pas de 'code'
                    "season": {"startDate": "2023-08-01"},
                }
            ]
        )
        out = transform(df)
        assert pd.isna(out["competition_code"].iloc[0])


# ---------------------------------------------------------------------------
# save_as_parquet
# ---------------------------------------------------------------------------


class TestSaveAsParquet:
    """Tests de la fonction save_as_parquet."""

    def test_calls_put_object_with_correct_bucket_and_key(self, config, raw_df):
        df = transform(raw_df)
        mock_s3 = MagicMock()

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            save_as_parquet(
                df, "my-bucket", "curated/PL/2023/matches.parquet", config=config
            )

        mock_s3.put_object.assert_called_once()
        kw = mock_s3.put_object.call_args[1]
        assert kw["Bucket"] == "my-bucket"
        assert kw["Key"] == "curated/PL/2023/matches.parquet"

    def test_returns_s3_uri(self, config, raw_df):
        df = transform(raw_df)
        mock_s3 = MagicMock()

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            uri = save_as_parquet(
                df, "my-bucket", "curated/PL/2023/matches.parquet", config=config
            )

        assert uri == "s3://my-bucket/curated/PL/2023/matches.parquet"

    def test_body_is_readable_parquet(self, config, raw_df):
        df = transform(raw_df)
        mock_s3 = MagicMock()

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            save_as_parquet(
                df, "my-bucket", "curated/PL/2023/matches.parquet", config=config
            )

        body: bytes = mock_s3.put_object.call_args[1]["Body"]
        result = pd.read_parquet(io.BytesIO(body))
        assert len(result) == len(df)
        assert "match_id" in result.columns

    def test_parquet_preserves_all_output_columns(self, config, raw_df):
        df = transform(raw_df)
        mock_s3 = MagicMock()

        with patch("src.transform.process_matches.boto3.client", return_value=mock_s3):
            save_as_parquet(
                df, "my-bucket", "curated/PL/2023/matches.parquet", config=config
            )

        body: bytes = mock_s3.put_object.call_args[1]["Body"]
        result = pd.read_parquet(io.BytesIO(body))
        assert set(df.columns) == set(result.columns)

    def test_raises_value_error_on_empty_dataframe(self, config):
        with pytest.raises(ValueError, match="vide"):
            save_as_parquet(pd.DataFrame(), "bucket", "key.parquet", config=config)

    def test_uses_region_from_config(self, config, raw_df):
        df = transform(raw_df)
        mock_s3 = MagicMock()

        with patch(
            "src.transform.process_matches.boto3.client", return_value=mock_s3
        ) as mock_client:
            save_as_parquet(
                df, "my-bucket", "curated/PL/2023/matches.parquet", config=config
            )

        mock_client.assert_called_once_with("s3", region_name="eu-west-1")


# ---------------------------------------------------------------------------
# build_curated_key
# ---------------------------------------------------------------------------


class TestBuildCuratedKey:
    """Tests de la fonction build_curated_key."""

    def test_format_with_int_season(self):
        assert build_curated_key("PL", 2023) == "curated/PL/2023/matches.parquet"

    def test_format_with_string_season(self):
        assert build_curated_key("BL1", "2022") == "curated/BL1/2022/matches.parquet"

    def test_starts_with_curated_prefix(self):
        assert build_curated_key("SA", 2021).startswith("curated/")

    def test_ends_with_parquet(self):
        assert build_curated_key("SA", 2021).endswith(".parquet")
