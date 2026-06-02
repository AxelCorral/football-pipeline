"""
Fixtures pytest partagées entre tous les modules de tests.

Fournit des instances de Settings factices et des données
de matchs brutes simulant la réponse de l'API football-data.org.
"""
import pytest

from src.config import Config


@pytest.fixture
def mock_settings() -> Config:
    """Instance Config avec des valeurs de test (sans appels AWS/API réels)."""
    return Config(
        api_key="test-api-key",
        aws_bucket_name="test-football-bucket",
        aws_region="eu-west-1",
        athena_database="football_test_db",
        athena_output_s3="s3://test-football-bucket/athena-results/",
        football_api_base_url="https://api.football-data.org/v4",
    )


@pytest.fixture
def sample_raw_matches() -> list[dict]:
    """Données de matchs brutes simulant la réponse de l'API football-data.org."""
    return [
        {
            "id": 123456,
            "utcDate": "2024-03-15T20:00:00Z",
            "status": "FINISHED",
            "homeTeam": {
                "id": 65,
                "name": "Manchester City FC",
                "shortName": "Man City",
            },
            "awayTeam": {"id": 57, "name": "Arsenal FC", "shortName": "Arsenal"},
            "score": {
                "winner": "HOME_TEAM",
                "fullTime": {"home": 3, "away": 1},
                "halfTime": {"home": 1, "away": 0},
            },
            "competition": {"id": 2021, "name": "Premier League"},
            "season": {
                "id": 1490,
                "startDate": "2023-08-11",
                "endDate": "2024-05-19",
            },
            "matchday": 29,
        },
    ]
