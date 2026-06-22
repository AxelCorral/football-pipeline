"""Tests du chargement de configuration."""

from src.config import Config
from src.config.settings import Settings


def test_settings_alias_preserves_backward_compatibility():
    assert Settings is Config


def test_load_reads_environment(monkeypatch):
    monkeypatch.setenv("API_KEY", "environment-key")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("ATHENA_DATABASE", "football_analytics")

    config = Config.load()

    assert config.api_key == "environment-key"
    assert config.aws_region == "us-east-1"
    assert config.athena_database == "football_analytics"


def test_load_overrides_environment(monkeypatch):
    monkeypatch.setenv("API_KEY", "environment-key")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    config = Config.load(api_key="explicit-key", aws_region="eu-west-3")

    assert config.api_key == "explicit-key"
    assert config.aws_region == "eu-west-3"


def test_load_uses_documented_defaults(monkeypatch):
    monkeypatch.delenv("FOOTBALL_API_BASE_URL", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    config = Config.load()

    assert config.football_api_base_url == "https://api.football-data.org/v4"
    assert config.aws_region == "eu-west-1"
