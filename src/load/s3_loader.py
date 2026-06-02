"""
Chargement des DataFrames sur AWS S3 au format Parquet.

Utilise boto3 et pyarrow pour sérialiser les données pandas
et les uploader sur S3 avec un chemin partitionné par date.
Schéma : {prefix}/year=YYYY/month=MM/day=DD/{filename}.parquet
"""

import logging
from datetime import date

import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)


class S3Loader:
    """Upload des DataFrames pandas vers S3 en format Parquet."""

    def __init__(self, settings: Config) -> None:
        pass

    def upload_dataframe(
        self,
        df: pd.DataFrame,
        prefix: str,
        partition_date: date,
        filename: str = "data.parquet",
    ) -> str:
        """Sérialise df en Parquet et l'uploade sur S3. Retourne l'URI S3."""
        pass

    def _build_s3_key(self, prefix: str, partition_date: date, filename: str) -> str:
        """Construit la clé S3 partitionnée par date Hive-style."""
        pass
