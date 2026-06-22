"""
Chargement des DataFrames sur AWS S3 au format Parquet.

Utilise boto3 et pyarrow pour sérialiser les données pandas
et les uploader sur S3 avec un chemin partitionné par date.
Schéma : {prefix}/year=YYYY/month=MM/day=DD/{filename}.parquet
"""

import io
import logging
from datetime import date

import boto3
import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)


class S3Loader:
    """Upload des DataFrames pandas vers S3 en format Parquet."""

    def __init__(self, settings: Config) -> None:
        self.bucket = settings.aws_bucket_name.strip()
        if not self.bucket:
            raise ValueError("Le nom du bucket S3 ne peut pas être vide")
        if not settings.aws_region.strip():
            raise ValueError("La région AWS ne peut pas être vide")
        self.s3 = boto3.client("s3", region_name=settings.aws_region)

    def upload_dataframe(
        self,
        df: pd.DataFrame,
        prefix: str,
        partition_date: date,
        filename: str = "data.parquet",
    ) -> str:
        """Sérialise df en Parquet et l'uploade sur S3. Retourne l'URI S3."""
        if df.empty:
            raise ValueError("Impossible d'uploader un DataFrame vide")

        key = self._build_s3_key(prefix, partition_date, filename)
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow")
        payload = buffer.getvalue()

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType="application/octet-stream",
        )
        uri = f"s3://{self.bucket}/{key}"
        logger.info("%d ligne(s) uploadée(s) vers %s", len(df), uri)
        return uri

    def _build_s3_key(self, prefix: str, partition_date: date, filename: str) -> str:
        """Construit la clé S3 partitionnée par date Hive-style."""
        clean_prefix = prefix.strip().strip("/")
        clean_filename = filename.strip().strip("/")
        if not clean_prefix:
            raise ValueError("Le préfixe S3 ne peut pas être vide")
        if not clean_filename:
            raise ValueError("Le nom de fichier S3 ne peut pas être vide")

        return (
            f"{clean_prefix}/year={partition_date.year}"
            f"/month={partition_date.month:02d}"
            f"/day={partition_date.day:02d}/{clean_filename}"
        )
