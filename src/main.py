"""
Point d'entrée du pipeline ETL football.

Orchestre les quatre étapes du pipeline pour un refresh incrémental
(saison courante, sans filtre season) :
  1. Extraction des matchs depuis l'API football-data.org
  2. Stockage brut sur S3 au format JSON (zone raw/)
  3. Transformation des données (normalisation, enrichissement)
  4. Stockage transformé sur S3 au format Parquet (zone curated/)

Pour un backfill multi-saisons explicite, voir scripts/ingest_all.py.
"""

import logging
from datetime import date

import pandas as pd

from src.config import Config
from src.ingestion.fetch_matches import fetch_all_competitions, upload_to_s3
from src.transform.process_matches import (
    build_curated_key,
    filter_by_season,
    load_raw_from_s3,
    save_as_parquet,
    transform,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

COMPETITIONS = ["PL", "FL1", "BL1", "SA", "PD"]


def run_pipeline(config: Config) -> dict[str, int]:
    """Exécute le pipeline ETL complet pour les 5 compétitions (saison courante).

    Pour chaque compétition : récupère les matchs via l'API, les uploade
    en JSON brut sur S3 (raw/), relit ce JSON, le transforme et le
    sauvegarde en Parquet (curated/). Une compétition qui échoue à
    n'importe quelle étape est journalisée et ignorée — elle ne bloque
    pas les autres.

    Args:
        config: Configuration du pipeline (credentials, bucket, etc.).

    Returns:
        Dict ``{competition_code: nombre de matchs curated}`` — 0 si la
        compétition a échoué ou n'a retourné aucun match.
    """
    if not config.aws_bucket_name:
        logger.error("AWS_BUCKET_NAME non défini — pipeline interrompu")
        return {}

    raw_results = fetch_all_competitions(COMPETITIONS, season=None, config=config)

    summary: dict[str, int] = {}
    for code in COMPETITIONS:
        try:
            matches = raw_results.get(code, [])
            if not matches:
                logger.warning("%s : aucun match récupéré, étape ignorée", code)
                summary[code] = 0
                continue

            upload_to_s3(matches, config.aws_bucket_name, code, config=config)

            df_raw = load_raw_from_s3(config.aws_bucket_name, code, config=config)
            if df_raw.empty:
                logger.warning("%s : relecture S3 vide, transform ignoré", code)
                summary[code] = 0
                continue

            df = transform(df_raw)
            available_seasons = pd.to_numeric(df["season"], errors="coerce").dropna()
            season = (
                int(available_seasons.max())
                if not available_seasons.empty
                else date.today().year
            )
            if not available_seasons.empty:
                df = filter_by_season(df, season)
            key = build_curated_key(code, season)
            save_as_parquet(df, config.aws_bucket_name, key, config=config)
            summary[code] = len(df)
            logger.info("%s : %d matchs curated → %s", code, len(df), key)
        except Exception:
            logger.exception("%s : échec du traitement, compétition ignorée", code)
            summary[code] = 0

    return summary


if __name__ == "__main__":
    run_pipeline(Config())
