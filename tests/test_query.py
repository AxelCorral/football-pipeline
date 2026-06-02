"""
Tests unitaires pour src/query/athena_query.py.

Couvre : soumission de requêtes, polling du statut d'exécution,
récupération paginée des résultats et gestion des timeouts/erreurs.
"""


class TestAthenaQueryRunner:
    """Tests du runner de requêtes Athena."""

    def test_run_query_returns_dataframe(self, mock_settings):
        """run_query doit retourner un DataFrame pandas."""
        pass

    def test_run_query_calls_start_query_execution(self, mock_settings):
        """run_query doit appeler start_query_execution sur le client Athena."""
        pass

    def test_wait_for_query_raises_on_failed_status(self, mock_settings):
        """_wait_for_query doit lever une exception si la requête échoue."""
        pass

    def test_wait_for_query_raises_on_timeout(self, mock_settings):
        """_wait_for_query doit lever une exception après MAX_WAIT_SECONDS."""
        pass

    def test_fetch_results_handles_pagination(self, mock_settings):
        """_fetch_results doit agréger toutes les pages de résultats."""
        pass
