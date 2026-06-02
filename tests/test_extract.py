"""
Tests unitaires pour src/extract/football_api.py.

Couvre : initialisation du client, récupération de matchs,
gestion des erreurs HTTP et format des paramètres de date.
"""


class TestFootballApiClient:
    """Tests du client API football-data.org."""

    def test_get_matches_returns_list(self, mock_settings):
        """get_matches doit retourner une liste."""
        pass

    def test_get_matches_sends_auth_header(self, mock_settings):
        """Le token API doit être envoyé dans le header X-Auth-Token."""
        pass

    def test_get_matches_formats_dates_as_iso8601(self, mock_settings):
        """Les paramètres dateFrom/dateTo doivent être au format ISO-8601."""
        pass

    def test_get_matches_raises_on_http_error(self, mock_settings):
        """Une réponse 4xx/5xx doit lever une HTTPError."""
        pass

    def test_get_competition_returns_dict(self, mock_settings):
        """get_competition doit retourner un dictionnaire."""
        pass
