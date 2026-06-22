"""Tests unitaires du runner de requêtes Athena."""

from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from src.query.athena_query import AthenaQueryRunner


class TestAthenaQueryRunner:
    """Vérifie la soumission, le polling et la pagination sans appel AWS."""

    @patch("src.query.athena_query.boto3.client")
    def test_run_query_returns_dataframe(self, mock_client_factory, mock_settings):
        client = mock_client_factory.return_value
        client.start_query_execution.return_value = {"QueryExecutionId": "query-123"}
        client.get_query_execution.return_value = {
            "QueryExecution": {"Status": {"State": "SUCCEEDED"}}
        }
        client.get_query_results.return_value = {
            "ResultSet": {
                "Rows": [
                    {"Data": [{"VarCharValue": "team"}, {"VarCharValue": "goals"}]},
                    {
                        "Data": [
                            {"VarCharValue": "Arsenal"},
                            {"VarCharValue": "42"},
                        ]
                    },
                ]
            }
        }

        result = AthenaQueryRunner(mock_settings).run_query("SELECT * FROM matches")

        pd.testing.assert_frame_equal(
            result, pd.DataFrame([["Arsenal", "42"]], columns=["team", "goals"])
        )

    @patch("src.query.athena_query.boto3.client")
    def test_run_query_calls_start_query_execution(
        self, mock_client_factory, mock_settings
    ):
        client = mock_client_factory.return_value
        client.start_query_execution.return_value = {"QueryExecutionId": "query-123"}
        runner = AthenaQueryRunner(mock_settings)
        runner._wait_for_query = MagicMock()
        runner._fetch_results = MagicMock(return_value=pd.DataFrame())

        runner.run_query("SELECT count(*) FROM matches")

        client.start_query_execution.assert_called_once_with(
            QueryString="SELECT count(*) FROM matches",
            QueryExecutionContext={"Database": mock_settings.athena_database},
            ResultConfiguration={"OutputLocation": mock_settings.athena_output_s3},
        )
        runner._wait_for_query.assert_called_once_with("query-123")
        runner._fetch_results.assert_called_once_with("query-123")

    @patch("src.query.athena_query.boto3.client")
    def test_wait_for_query_raises_on_failed_status(
        self, mock_client_factory, mock_settings
    ):
        mock_client_factory.return_value.get_query_execution.return_value = {
            "QueryExecution": {
                "Status": {
                    "State": "FAILED",
                    "StateChangeReason": "SQL invalide",
                }
            }
        }

        with pytest.raises(RuntimeError, match="FAILED.*SQL invalide"):
            AthenaQueryRunner(mock_settings)._wait_for_query("query-failed")

    @patch("src.query.athena_query.time.sleep")
    @patch("src.query.athena_query.MAX_WAIT_SECONDS", 2)
    @patch("src.query.athena_query.POLL_INTERVAL_SECONDS", 1)
    @patch("src.query.athena_query.boto3.client")
    def test_wait_for_query_raises_on_timeout(
        self, mock_client_factory, mock_sleep, mock_settings
    ):
        client = mock_client_factory.return_value
        client.get_query_execution.return_value = {
            "QueryExecution": {"Status": {"State": "RUNNING"}}
        }

        with pytest.raises(TimeoutError, match="après 2s"):
            AthenaQueryRunner(mock_settings)._wait_for_query("query-running")

        assert client.get_query_execution.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("src.query.athena_query.boto3.client")
    def test_fetch_results_handles_pagination(self, mock_client_factory, mock_settings):
        client = mock_client_factory.return_value
        client.get_query_results.side_effect = [
            {
                "ResultSet": {
                    "Rows": [
                        {
                            "Data": [
                                {"VarCharValue": "team"},
                                {"VarCharValue": "goals"},
                            ]
                        },
                        {
                            "Data": [
                                {"VarCharValue": "Arsenal"},
                                {"VarCharValue": "42"},
                            ]
                        },
                    ]
                },
                "NextToken": "page-2",
            },
            {
                "ResultSet": {
                    "Rows": [
                        {
                            "Data": [
                                {"VarCharValue": "Liverpool"},
                                {},
                            ]
                        }
                    ]
                }
            },
        ]

        result = AthenaQueryRunner(mock_settings)._fetch_results("query-123")

        pd.testing.assert_frame_equal(
            result,
            pd.DataFrame(
                [["Arsenal", "42"], ["Liverpool", None]],
                columns=["team", "goals"],
            ),
        )
        assert client.get_query_results.call_args_list == [
            call(QueryExecutionId="query-123", MaxResults=1000),
            call(
                QueryExecutionId="query-123",
                MaxResults=1000,
                NextToken="page-2",
            ),
        ]
