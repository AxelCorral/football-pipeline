"""
Point d'entrée du pipeline ETL football.

Orchestre les quatre étapes du pipeline :
  1. Extraction des matchs depuis l'API football-data.org
  2. Stockage brut sur S3 au format Parquet (zone raw/)
  3. Transformation des données (normalisation, enrichissement)
  4. Stockage transformé sur S3 (zone curated/)
"""
import logging
from datetime import date, timedelta

from src.config import Config
from src.extract.football_api import FootballApiClient
from src.load.s3_loader import S3Loader
from src.query.athena_query import AthenaQueryRunner
from src.transform.glue_transform import GlueTransformer

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
