"""
Tests unitaires pour src/ingestion/fetch_matches.py.

Couvre : récupération API avec retry, upload S3 JSON, construction de clé.
Aucun appel réel : requests et boto3 sont entièrement mockés.
"""
import json
from datetime import date
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from src.config import Config
from src.ingestion.fetch_matches import build_s3_key, get_matches, upload_to_s3


@pytest.fixture
def config() -> Config:
    return Config(
        api_key="test-api-key",
        aws_bucket_name="test-bucket",
        aws_region="eu-west-1",
        athena_database="test_db",
        athena_output_s3="s3://test-bucket/athena/",
        football_api_base_url="https://api.football-data.org/v4",
    )


@pytest.fixture
def sample_matches() -> list[dict]:
    return [
        {
            "id": 123456,
            "utcDate": "2024-03-15T20:00:00Z",
            "status": "FINISHED",
            "homeTeam": {"id": 65, "name": "Manchester City FC"},
            "awayTeam": {"id": 57, "name": "Arsenal FC"},
            "score": {"winner": "HOME_TEAM", "fullTime": {"home": 3, "away": 1}},
        }
    ]


def _mock_response(status_code: int = 200, json_body: dict | None = None) -> MagicMock:
    """Fabrique une fausse réponse requests."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    if status_code >= 400:
        http_err = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestGetMatches:
    """Tests de la fonction get_matches."""

    def test_returns_matches_list(self, config, sample_matches):
        """Doit retourner la liste 'matches' du payload API."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, {"matches": sample_matches})
            result = get_matches("PL", 2023, config=config)

        assert result == sample_matches

    def test_sends_auth_header(self, config):
        """Le token API doit être transmis dans X-Auth-Token."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, {"matches": []})
            get_matches("PL", 2023, config=config)

        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["X-Auth-Token"] == "test-api-key"

    def test_season_included_in_params_when_provided(self, config):
        """season fourni → présent dans les query params du premier appel."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, {"matches": []})
            get_matches("BL1", 2022, config=config)

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["season"] == 2022

    def test_season_absent_from_params_when_none(self, config):
        """season=None → paramètre absent des query params."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, {"matches": []})
            get_matches("PL", config=config)

        _, kwargs = mock_get.call_args
        assert "season" not in kwargs["params"]

    def test_builds_url_from_config(self, config):
        """L'URL doit utiliser football_api_base_url de la config."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, {"matches": []})
            get_matches("SA", 2023, config=config)

        url_called = mock_get.call_args[0][0]
        assert url_called == "https://api.football-data.org/v4/competitions/SA/matches"

    def test_returns_empty_list_when_no_matches_key(self, config):
        """Un payload sans clé 'matches' doit retourner une liste vide."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, {})
            result = get_matches("PL", 2023, config=config)

        assert result == []

    def test_raises_immediately_on_non_400_4xx(self, config):
        """Une erreur 4xx autre que 400 doit être levée sans retry ni fallback."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(404)

            with pytest.raises(requests.HTTPError):
                get_matches("PL", 2023, config=config)

        assert mock_get.call_count == 1  # aucun retry, aucun fallback

    # ------------------------------------------------------------------
    # Fallback 400 : suppression du paramètre season
    # ------------------------------------------------------------------

    def test_fallback_on_400_retries_without_season(self, config, sample_matches):
        """400 avec season → second appel sans le paramètre season."""
        responses = [
            _mock_response(400),
            _mock_response(200, {"matches": sample_matches}),
        ]
        with patch("src.ingestion.fetch_matches.requests.get", side_effect=responses) as mock_get:
            get_matches("PL", 2024, config=config)

        assert mock_get.call_count == 2
        _, kwargs_fallback = mock_get.call_args  # dernier appel = fallback
        assert "season" not in kwargs_fallback["params"]

    def test_fallback_returns_correct_matches(self, config, sample_matches):
        """Le résultat du fallback sans season doit être retourné."""
        responses = [
            _mock_response(400),
            _mock_response(200, {"matches": sample_matches}),
        ]
        with patch("src.ingestion.fetch_matches.requests.get", side_effect=responses):
            result = get_matches("PL", 2024, config=config)

        assert result == sample_matches

    def test_fallback_not_triggered_when_season_is_none(self, config):
        """400 sans season fourni → levée immédiate, pas de fallback."""
        with patch("src.ingestion.fetch_matches.requests.get") as mock_get:
            mock_get.return_value = _mock_response(400)

            with pytest.raises(requests.HTTPError):
                get_matches("PL", config=config)  # season=None

        assert mock_get.call_count == 1

    def test_raises_if_fallback_also_fails(self, config):
        """Si le fallback sans season échoue aussi (400), l'erreur est propagée."""
        with patch(
            "src.ingestion.fetch_matches.requests.get",
            side_effect=[_mock_response(400), _mock_response(400)],
        ):
            with pytest.raises(requests.HTTPError):
                get_matches("PL", 2024, config=config)

    def test_400_fallback_does_not_consume_retries(self, config, sample_matches):
        """Le fallback 400 est distinct des 3 retries transients : 2 appels max."""
        responses = [_mock_response(400), _mock_response(200, {"matches": sample_matches})]
        with patch("src.ingestion.fetch_matches.requests.get", side_effect=responses) as mock_get:
            get_matches("PL", 2024, config=config)

        assert mock_get.call_count == 2  # pas 3, pas 4

    # ------------------------------------------------------------------
    # Retry sur erreurs transientes (5xx, réseau)
    # ------------------------------------------------------------------

    def test_retries_on_server_error_then_succeeds(self, config, sample_matches):
        """Deux erreurs 500 suivies d'un 200 : doit réussir au 3e essai."""
        responses = [
            _mock_response(500),
            _mock_response(500),
            _mock_response(200, {"matches": sample_matches}),
        ]
        with (
            patch("src.ingestion.fetch_matches.requests.get", side_effect=responses) as mock_get,
            patch("src.ingestion.fetch_matches.time.sleep"),
        ):
            result = get_matches("PL", 2023, config=config)

        assert result == sample_matches
        assert mock_get.call_count == 3

    def test_raises_runtime_error_after_max_retries(self, config):
        """Trois erreurs 500 consécutives : doit lever RuntimeError."""
        with (
            patch(
                "src.ingestion.fetch_matches.requests.get",
                side_effect=[_mock_response(500)] * 3,
            ),
            patch("src.ingestion.fetch_matches.time.sleep"),
        ):
            with pytest.raises(RuntimeError, match="3 tentatives"):
                get_matches("PL", 2023, config=config)

    def test_retry_sleeps_with_exponential_backoff(self, config):
        """Les délais entre retries doivent suivre 2^1, 2^2 secondes."""
        with (
            patch(
                "src.ingestion.fetch_matches.requests.get",
                side_effect=[_mock_response(503)] * 3,
            ),
            patch("src.ingestion.fetch_matches.time.sleep") as mock_sleep,
        ):
            with pytest.raises(RuntimeError):
                get_matches("PL", 2023, config=config)

        assert mock_sleep.call_args_list == [call(2), call(4)]

    def test_retries_on_connection_error(self, config, sample_matches):
        """Une ConnectionError réseau doit déclencher un retry."""
        responses = [
            requests.ConnectionError("timeout"),
            _mock_response(200, {"matches": sample_matches}),
        ]
        with (
            patch("src.ingestion.fetch_matches.requests.get", side_effect=responses),
            patch("src.ingestion.fetch_matches.time.sleep"),
        ):
            result = get_matches("PL", 2023, config=config)

        assert result == sample_matches

    def test_retries_on_429_rate_limit(self, config, sample_matches):
        """Un 429 Too Many Requests doit être retryé."""
        responses = [
            _mock_response(429),
            _mock_response(200, {"matches": sample_matches}),
        ]
        with (
            patch("src.ingestion.fetch_matches.requests.get", side_effect=responses),
            patch("src.ingestion.fetch_matches.time.sleep"),
        ):
            result = get_matches("PL", 2023, config=config)

        assert result == sample_matches


class TestUploadToS3:
    """Tests de la fonction upload_to_s3."""

    def test_calls_put_object(self, config, sample_matches):
        """put_object doit être appelé avec le bucket et la clé construite."""
        mock_s3 = MagicMock()
        with patch("src.ingestion.fetch_matches.boto3.client", return_value=mock_s3):
            upload_to_s3(sample_matches, "my-bucket", "PL", date(2024, 3, 15), config=config)

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "my-bucket"
        assert call_kwargs["Key"] == "raw/PL/2024-03-15/matches.json"

    def test_returns_s3_uri(self, config, sample_matches):
        """Doit retourner une URI s3:// avec la clé construite."""
        mock_s3 = MagicMock()
        with patch("src.ingestion.fetch_matches.boto3.client", return_value=mock_s3):
            uri = upload_to_s3(sample_matches, "my-bucket", "PL", date(2024, 3, 15), config=config)

        assert uri == "s3://my-bucket/raw/PL/2024-03-15/matches.json"

    def test_body_is_valid_json(self, config, sample_matches):
        """Le corps uploadé doit être du JSON valide décodable."""
        mock_s3 = MagicMock()
        with patch("src.ingestion.fetch_matches.boto3.client", return_value=mock_s3):
            upload_to_s3(sample_matches, "my-bucket", "PL", date(2024, 3, 15), config=config)

        body: bytes = mock_s3.put_object.call_args[1]["Body"]
        parsed = json.loads(body.decode("utf-8"))
        assert parsed == sample_matches

    def test_content_type_is_json(self, config, sample_matches):
        """Le ContentType doit être application/json."""
        mock_s3 = MagicMock()
        with patch("src.ingestion.fetch_matches.boto3.client", return_value=mock_s3):
            upload_to_s3(sample_matches, "my-bucket", "PL", date(2024, 3, 15), config=config)

        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "application/json"

    def test_uses_aws_region_from_config(self, config):
        """boto3.client doit utiliser la région de la config."""
        mock_s3 = MagicMock()
        with patch("src.ingestion.fetch_matches.boto3.client", return_value=mock_s3) as mock_client:
            upload_to_s3([], "my-bucket", "PL", date(2024, 3, 15), config=config)

        mock_client.assert_called_once_with("s3", region_name="eu-west-1")

    def test_key_uses_today_when_no_date(self, config):
        """Sans date explicite, la clé doit utiliser la date du jour."""
        mock_s3 = MagicMock()
        with (
            patch("src.ingestion.fetch_matches.boto3.client", return_value=mock_s3),
            patch("src.ingestion.fetch_matches.date") as mock_date,
        ):
            mock_date.today.return_value = date(2024, 6, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            upload_to_s3([], "my-bucket", "BL1", config=config)

        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Key"] == "raw/BL1/2024-06-01/matches.json"


class TestBuildS3Key:
    """Tests de la fonction build_s3_key."""

    def test_format_with_explicit_date(self):
        """La clé doit suivre le format raw/{code}/{date}/matches.json."""
        key = build_s3_key("PL", date(2024, 3, 15))
        assert key == "raw/PL/2024-03-15/matches.json"

    def test_uses_today_when_no_date(self):
        """Sans date explicite, la date du jour doit être utilisée."""
        with patch("src.ingestion.fetch_matches.date") as mock_date:
            mock_date.today.return_value = date(2024, 6, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            key = build_s3_key("BL1")

        assert key == "raw/BL1/2024-06-01/matches.json"

    def test_competition_code_in_key(self):
        """Le code de compétition doit apparaître dans la clé."""
        key = build_s3_key("SA", date(2024, 1, 1))
        assert "SA" in key
