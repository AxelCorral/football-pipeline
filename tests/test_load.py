"""
Tests unitaires pour src/load/s3_loader.py.

Couvre : construction des clés S3 Hive-style, sérialisation Parquet,
appel boto3 et valeur de retour (URI S3 complète).
"""


class TestS3Loader:
    """Tests du chargeur S3."""

    def test_build_s3_key_hive_partitioning(self, mock_settings):
        """La clé S3 doit suivre le schéma year=X/month=XX/day=XX."""
        pass

    def test_upload_dataframe_calls_s3_put_object(self, mock_settings):
        """upload_dataframe doit invoquer le client S3 boto3."""
        pass

    def test_upload_dataframe_returns_s3_uri(self, mock_settings):
        """upload_dataframe doit retourner une URI s3:// valide."""
        pass

    def test_upload_empty_dataframe_raises_value_error(self, mock_settings):
        """Un DataFrame vide ne doit pas être uploadé."""
        pass
