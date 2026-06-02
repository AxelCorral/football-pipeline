"""
Configuration du pipeline — chargement automatique depuis .env.

Usage production (sans arguments) :
    from src.config import Config
    config = Config()

Usage test (valeurs nommées, prioritaires sur l'environnement) :
    config = Config(api_key="test-key", aws_region="eu-west-1", ...)

Variables d'environnement attendues (voir .env.example) :
    API_KEY, FOOTBALL_API_BASE_URL,
    AWS_BUCKET_NAME, AWS_REGION,
    ATHENA_DATABASE, ATHENA_OUTPUT_S3
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Chargé une fois à l'import du module ; n'écrase pas les variables déjà
# définies dans l'environnement (comportement par défaut de load_dotenv).
load_dotenv()


def _env(name: str, default: str = "") -> str:
    """Lit une variable d'environnement, retourne default si absente."""
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    """Configuration complète du pipeline.

    Sans arguments tous les champs sont lus depuis l'environnement.
    Les arguments nommés prennent la priorité sur l'environnement,
    ce qui permet de construire une config de test sans fichier .env.
    """

    api_key: str = field(
        default_factory=lambda: _env("API_KEY")
    )
    football_api_base_url: str = field(
        default_factory=lambda: _env("FOOTBALL_API_BASE_URL", "https://api.football-data.org/v4")
    )
    aws_bucket_name: str = field(
        default_factory=lambda: _env("AWS_BUCKET_NAME")
    )
    aws_region: str = field(
        default_factory=lambda: _env("AWS_REGION", "eu-west-1")
    )
    athena_database: str = field(
        default_factory=lambda: _env("ATHENA_DATABASE")
    )
    athena_output_s3: str = field(
        default_factory=lambda: _env("ATHENA_OUTPUT_S3")
    )
