"""
Transformations pandas simulant un job AWS Glue.

Normalise et enrichit les données brutes de matchs :
  - Aplatissement des champs imbriqués (équipes, score, arbitres)
  - Typage correct des colonnes (dates, entiers, flottants)
  - Ajout de colonnes de partitionnement Hive (year, month, day)
  - Déduplication et filtrage des matchs invalides
"""

import logging
from typing import Any

import pandas as pd

from src.transform.process_matches import transform as normalize_matches

logger = logging.getLogger(__name__)


class GlueTransformer:
    """Transforme les données brutes de l'API en DataFrame Parquet-ready."""

    def transform(self, raw_matches: list[dict[str, Any]]) -> pd.DataFrame:
        """Convertit une liste de matchs bruts en DataFrame normalisé."""
        normalized = normalize_matches(pd.json_normalize(raw_matches))
        if normalized.empty:
            return self._add_partition_columns(normalized)

        valid = normalized.dropna(subset=["match_id", "date", "home_team", "away_team"])
        deduplicated = valid.drop_duplicates(subset=["match_id"], keep="last")

        removed = len(normalized) - len(deduplicated)
        if removed:
            logger.warning("%d match(s) invalide(s) ou dupliqué(s) ignoré(s)", removed)

        return self._add_partition_columns(deduplicated).reset_index(drop=True)

    def _flatten_match(self, match: dict[str, Any]) -> dict[str, Any]:
        """Aplatit un objet match imbriqué en dictionnaire plat."""
        normalized = normalize_matches(pd.json_normalize([match]))
        return normalized.iloc[0].to_dict()

    def _add_partition_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute les colonnes year/month/day pour le partitionnement S3."""
        partitioned = df.copy()
        dates = pd.to_datetime(partitioned["date"], utc=True, errors="coerce")
        partitioned["year"] = dates.dt.year.astype("Int64")
        partitioned["month"] = dates.dt.month.astype("Int64")
        partitioned["day"] = dates.dt.day.astype("Int64")
        return partitioned
