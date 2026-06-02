"""
Point d'entrée du pipeline ETL football.

Orchestre les quatre étapes du pipeline :
  1. Extraction des matchs depuis l'API football-data.org
  2. Stockage brut sur S3 au format Parquet (zone raw/)
  3. Transformation des données (normalisation, enrichissement)
  4. Stockage transformé sur S3 (zone curated/)
"""

import logging

from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

PREMIER_LEAGUE_ID = 2021


def run_pipeline(config: Config) -> None:
    """Exécute le pipeline ETL complet pour la journée précédente."""
    pass


if __name__ == "__main__":
    run_pipeline(Config())
