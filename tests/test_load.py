"""Tests unitaires pour src/load/s3_loader.py."""

from dataclasses import replace
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.load.s3_loader import S3Loader


class TestS3Loader:
    """Tests du chargeur S3."""

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("aws_bucket_name", None, "bucket S3.*chaîne"),
            ("aws_region", 123, "région AWS.*chaîne"),
        ],
    )
    def test_init_rejects_non_string_configuration(
        self, mock_settings, field, value, message
    ):
        settings = replace(mock_settings, **{field: value})

        with patch("src.load.s3_loader.boto3.client") as boto3_client:
            with pytest.raises(ValueError, match=message):
                S3Loader(settings)

        boto3_client.assert_not_called()

    def test_init_rejects_empty_bucket_name(self, mock_settings):
        settings = replace(mock_settings, aws_bucket_name=" ")

        with patch("src.load.s3_loader.boto3.client") as boto3_client:
            with pytest.raises(ValueError, match="bucket S3"):
                S3Loader(settings)

        boto3_client.assert_not_called()

    def test_init_rejects_empty_aws_region(self, mock_settings):
        settings = replace(mock_settings, aws_region=" \n ")

        with patch("src.load.s3_loader.boto3.client") as boto3_client:
            with pytest.raises(ValueError, match="région AWS"):
                S3Loader(settings)

        boto3_client.assert_not_called()

    def test_build_s3_key_hive_partitioning(self, mock_settings):
        with patch("src.load.s3_loader.boto3.client"):
            loader = S3Loader(mock_settings)

        key = loader._build_s3_key("curated", date(2024, 3, 5), "matches.parquet")

        assert key == "curated/year=2024/month=03/day=05/matches.parquet"

    def test_build_s3_key_rejects_invalid_partition_date(self, mock_settings):
        with patch("src.load.s3_loader.boto3.client"):
            loader = S3Loader(mock_settings)

        with pytest.raises(ValueError, match="date de partition S3"):
            loader._build_s3_key("curated", "2024-03-05", "matches.parquet")

    @pytest.mark.parametrize(
        ("prefix", "filename", "message"),
        [
            (None, "matches.parquet", "préfixe S3.*chaîne"),
            ("curated", 123, "nom de fichier S3.*chaîne"),
        ],
    )
    def test_build_s3_key_rejects_non_string_components(
        self, mock_settings, prefix, filename, message
    ):
        with patch("src.load.s3_loader.boto3.client"):
            loader = S3Loader(mock_settings)

        with pytest.raises(ValueError, match=message):
            loader._build_s3_key(prefix, date(2024, 3, 5), filename)

    @pytest.mark.parametrize(
        ("prefix", "filename", "message"),
        [
            (" / ", "matches.parquet", "préfixe S3"),
            ("curated", " / ", "nom de fichier S3"),
        ],
    )
    def test_build_s3_key_rejects_empty_components(
        self, mock_settings, prefix, filename, message
    ):
        with patch("src.load.s3_loader.boto3.client"):
            loader = S3Loader(mock_settings)

        with pytest.raises(ValueError, match=message):
            loader._build_s3_key(prefix, date(2024, 3, 5), filename)

    @pytest.mark.parametrize(
        "filename", ["archive/matches.parquet", r"archive\matches"]
    )
    def test_build_s3_key_rejects_filename_path_separators(
        self, mock_settings, filename
    ):
        with patch("src.load.s3_loader.boto3.client"):
            loader = S3Loader(mock_settings)

        with pytest.raises(ValueError, match="séparateur"):
            loader._build_s3_key("curated", date(2024, 3, 5), filename)

    def test_upload_dataframe_calls_s3_put_object(self, mock_settings):
        settings = replace(mock_settings, aws_region=" eu-west-1 ")
        s3 = MagicMock()
        df = pd.DataFrame({"match_id": [1], "home_team": ["Arsenal"]})

        with patch("src.load.s3_loader.boto3.client", return_value=s3) as boto3_client:
            S3Loader(settings).upload_dataframe(
                df, "curated", date(2024, 3, 5), "matches.parquet"
            )

        boto3_client.assert_called_once_with("s3", region_name="eu-west-1")
        kwargs = s3.put_object.call_args.kwargs
        assert kwargs["Bucket"] == "test-football-bucket"
        assert kwargs["Key"] == "curated/year=2024/month=03/day=05/matches.parquet"
        assert kwargs["ContentType"] == "application/octet-stream"
        assert isinstance(kwargs["Body"], bytes)

    def test_upload_dataframe_returns_s3_uri(self, mock_settings):
        with patch("src.load.s3_loader.boto3.client", return_value=MagicMock()):
            uri = S3Loader(mock_settings).upload_dataframe(
                pd.DataFrame({"match_id": [1]}),
                "curated",
                date(2024, 3, 5),
            )

        assert (
            uri
            == "s3://test-football-bucket/curated/year=2024/month=03/day=05/data.parquet"
        )

    def test_upload_empty_dataframe_raises_value_error(self, mock_settings):
        with patch("src.load.s3_loader.boto3.client"):
            loader = S3Loader(mock_settings)

        with pytest.raises(ValueError, match="DataFrame vide"):
            loader.upload_dataframe(pd.DataFrame(), "curated", date(2024, 3, 5))

    @pytest.mark.parametrize("invalid_data", [None, [], {"match_id": [1]}])
    def test_upload_rejects_non_dataframe_before_s3_call(
        self, mock_settings, invalid_data
    ):
        s3 = MagicMock()
        with patch("src.load.s3_loader.boto3.client", return_value=s3):
            loader = S3Loader(mock_settings)

        with pytest.raises(TypeError, match="DataFrame pandas"):
            loader.upload_dataframe(invalid_data, "curated", date(2024, 3, 5))

        s3.put_object.assert_not_called()
