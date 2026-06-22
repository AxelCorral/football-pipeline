"""
Tests unitaires pour src/extract/football_api.py.

Couvre : initialisation du client, récupération de matchs,
gestion des erreurs HTTP et format des paramètres de date.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.extract.football_api import FootballApiClient


class TestFootballApiClient:
    """Tests du client API football-data.org."""

    def test_get_matches_returns_list(self, mock_settings):
        """get_matches doit retourner une liste."""
        response = MagicMock()
        response.json.return_value = {"matches": [{"id": 1}]}

        with patch("src.extract.football_api.requests.get", return_value=response):
            matches = FootballApiClient(mock_settings).get_matches(
                2021, date(2024, 1, 1), date(2024, 1, 31)
            )

        assert matches == [{"id": 1}]

    def test_get_matches_sends_auth_header(self, mock_settings):
        """Le token API doit être envoyé dans le header X-Auth-Token."""
        response = MagicMock()
        response.json.return_value = {"matches": []}

        with patch(
            "src.extract.football_api.requests.get", return_value=response
        ) as mock_get:
            FootballApiClient(mock_settings).get_matches(
                2021, date(2024, 1, 1), date(2024, 1, 31)
            )

        assert mock_get.call_args.kwargs["headers"] == {"X-Auth-Token": "test-api-key"}

    def test_get_matches_formats_dates_as_iso8601(self, mock_settings):
        """Les paramètres dateFrom/dateTo doivent être au format ISO-8601."""
        response = MagicMock()
        response.json.return_value = {"matches": []}

        with patch(
            "src.extract.football_api.requests.get", return_value=response
        ) as mock_get:
            FootballApiClient(mock_settings).get_matches(
                2021, date(2024, 1, 2), date(2024, 3, 4)
            )

        assert mock_get.call_args.kwargs["params"] == {
            "dateFrom": "2024-01-02",
            "dateTo": "2024-03-04",
        }

    def test_get_matches_raises_on_http_error(self, mock_settings):
        """Une réponse 4xx/5xx doit lever une HTTPError."""
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("403")

        with patch("src.extract.football_api.requests.get", return_value=response):
            with pytest.raises(requests.HTTPError, match="403"):
                FootballApiClient(mock_settings).get_matches(
                    2021, date(2024, 1, 1), date(2024, 1, 31)
                )

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            ([], "objet JSON attendu"),
            ({"matches": {}}, "'matches' doit être une liste"),
        ],
    )
    def test_get_matches_rejects_invalid_payload(self, mock_settings, payload, message):
        """Une réponse JSON mal formée doit produire une erreur explicite."""
        response = MagicMock()
        response.json.return_value = payload

        with patch("src.extract.football_api.requests.get", return_value=response):
            with pytest.raises(ValueError, match=message):
                FootballApiClient(mock_settings).get_matches(
                    2021, date(2024, 1, 1), date(2024, 1, 31)
                )

    def test_get_competition_returns_dict(self, mock_settings):
        """get_competition doit retourner un dictionnaire."""
        response = MagicMock()
        response.json.return_value = {"id": 2021, "name": "Premier League"}

        with patch("src.extract.football_api.requests.get", return_value=response):
            competition = FootballApiClient(mock_settings).get_competition(2021)

        assert competition == {"id": 2021, "name": "Premier League"}

    def test_get_competition_rejects_non_object_payload(self, mock_settings):
        """Les métadonnées de compétition doivent être un objet JSON."""
        response = MagicMock()
        response.json.return_value = []

        with patch("src.extract.football_api.requests.get", return_value=response):
            with pytest.raises(ValueError, match="objet JSON attendu"):
                FootballApiClient(mock_settings).get_competition(2021)
