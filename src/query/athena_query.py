"""
Exécution de requêtes SQL sur AWS Athena.

Lance des requêtes sur les tables Glue/Athena pointant vers les données
Parquet curées sur S3. Gère le polling du statut et la pagination
des résultats via l'API boto3.
"""
import logging
import time
from typing import Any

import boto3
import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2
MAX_WAIT_SECONDS = 300


class AthenaQueryRunner:
    """Lance des requêtes SQL sur Athena et retourne les résultats."""

    def __init__(self, settings: Config) -> None:
        pass

    def run_query(self, sql: str) -> pd.DataFrame:
        """Exécute une requête SQL et retourne les résultats sous forme de DataFrame."""
        pass

    def _wait_for_query(self, query_execution_id: str) -> None:
        """Bloque jusqu'à la fin de la requête ou lève une exception."""
        pass

    def _fetch_results(self, query_execution_id: str) -> pd.DataFrame:
        """Récupère et agrège les pages de résultats d'une requête terminée."""
        pass
