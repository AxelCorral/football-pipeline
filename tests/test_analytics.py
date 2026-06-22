"""Tests de l'API fonctionnelle Athena, sans appel AWS réel."""

from dataclasses import replace
from unittest.mock import call, patch

import pandas as pd
import pytest

from src.analytics.athena_queries import (
    _wait_for_completion,
    results_to_dataframe,
    run_athena_query,
)


@patch("src.analytics.athena_queries._wait_for_completion")
@patch("src.analytics.athena_queries.boto3.client")
def test_run_athena_query_submits_configured_request(
    mock_client_factory, mock_wait, mock_settings
):
    client = mock_client_factory.return_value
    client.start_query_execution.return_value = {"QueryExecutionId": "query-123"}

    result = run_athena_query(
        "SELECT 1",
        mock_settings.athena_database,
        mock_settings.athena_output_s3,
        config=mock_settings,
    )

    assert result == "query-123"
    client.start_query_execution.assert_called_once_with(
        QueryString="SELECT 1",
        QueryExecutionContext={"Database": mock_settings.athena_database},
        ResultConfiguration={"OutputLocation": mock_settings.athena_output_s3},
    )
    mock_wait.assert_called_once_with(client, "query-123")


@patch("src.analytics.athena_queries.boto3.client")
def test_run_athena_query_rejects_empty_sql(mock_client_factory, mock_settings):
    with pytest.raises(ValueError, match="requête SQL"):
        run_athena_query(
            " \n ",
            mock_settings.athena_database,
            mock_settings.athena_output_s3,
            config=mock_settings,
        )

    mock_client_factory.assert_not_called()


@pytest.mark.parametrize(
    ("database", "output_s3", "message"),
    [
        (" \n ", "s3://bucket/results/", "base Athena"),
        ("analytics", " \n ", "emplacement S3"),
    ],
)
@patch("src.analytics.athena_queries.boto3.client")
def test_run_athena_query_rejects_empty_destination(
    mock_client_factory, database, output_s3, message, mock_settings
):
    with pytest.raises(ValueError, match=message):
        run_athena_query(
            "SELECT 1",
            database,
            output_s3,
            config=mock_settings,
        )

    mock_client_factory.assert_not_called()


@patch("src.analytics.athena_queries.boto3.client")
def test_run_athena_query_rejects_empty_aws_region(mock_client_factory, mock_settings):
    config = replace(mock_settings, aws_region=" \n ")

    with pytest.raises(ValueError, match="région AWS"):
        run_athena_query(
            "SELECT 1",
            config.athena_database,
            config.athena_output_s3,
            config=config,
        )

    mock_client_factory.assert_not_called()


@patch("src.analytics.athena_queries.boto3.client")
def test_results_to_dataframe_rejects_empty_query_id(
    mock_client_factory, mock_settings
):
    with pytest.raises(ValueError, match="identifiant d'exécution Athena"):
        results_to_dataframe(" \n ", config=mock_settings)

    mock_client_factory.assert_not_called()


@patch("src.analytics.athena_queries.boto3.client")
def test_results_to_dataframe_rejects_empty_aws_region(
    mock_client_factory, mock_settings
):
    config = replace(mock_settings, aws_region=" \n ")

    with pytest.raises(ValueError, match="région AWS"):
        results_to_dataframe("query-123", config=config)

    mock_client_factory.assert_not_called()


@patch("src.analytics.athena_queries.boto3.client")
def test_results_to_dataframe_handles_pagination_and_nulls(
    mock_client_factory, mock_settings
):
    client = mock_client_factory.return_value
    client.get_query_results.side_effect = [
        {
            "ResultSet": {
                "ResultSetMetadata": {
                    "ColumnInfo": [{"Name": "team"}, {"Name": "goals"}]
                },
                "Rows": [
                    {"Data": [{"VarCharValue": "team"}, {"VarCharValue": "goals"}]},
                    {
                        "Data": [
                            {"VarCharValue": "Arsenal"},
                            {"VarCharValue": "42"},
                        ]
                    },
                ],
            },
            "NextToken": "page-2",
        },
        {"ResultSet": {"Rows": [{"Data": [{"VarCharValue": "Liverpool"}, {}]}]}},
    ]

    result = results_to_dataframe("query-123", config=mock_settings)

    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame(
            [["Arsenal", "42"], ["Liverpool", None]],
            columns=["team", "goals"],
        ),
    )
    assert client.get_query_results.call_args_list == [
        call(QueryExecutionId="query-123", MaxResults=1000),
        call(QueryExecutionId="query-123", MaxResults=1000, NextToken="page-2"),
    ]


@patch("src.analytics.athena_queries.boto3.client")
def test_results_to_dataframe_handles_empty_result(mock_client_factory, mock_settings):
    mock_client_factory.return_value.get_query_results.return_value = {
        "ResultSet": {
            "ResultSetMetadata": {"ColumnInfo": [{"Name": "team"}, {"Name": "goals"}]},
            "Rows": [],
        }
    }

    result = results_to_dataframe("query-empty", config=mock_settings)

    assert result.empty
    assert list(result.columns) == ["team", "goals"]


@patch("src.analytics.athena_queries.time.sleep")
def test_wait_for_completion_raises_failed_reason(mock_sleep):
    client = type("Client", (), {})()
    client.get_query_execution = lambda **_: {
        "QueryExecution": {
            "Status": {"State": "FAILED", "StateChangeReason": "SQL invalide"}
        }
    }

    with pytest.raises(RuntimeError, match="FAILED.*SQL invalide"):
        _wait_for_completion(client, "query-failed")

    mock_sleep.assert_called_once()


@patch("src.analytics.athena_queries.MAX_WAIT_SECONDS", 2)
@patch("src.analytics.athena_queries.POLL_INTERVAL_SECONDS", 1)
@patch("src.analytics.athena_queries.time.sleep")
def test_wait_for_completion_times_out(mock_sleep):
    client = type("Client", (), {})()
    client.get_query_execution = lambda **_: {
        "QueryExecution": {"Status": {"State": "RUNNING"}}
    }

    with pytest.raises(TimeoutError, match="après 2s"):
        _wait_for_completion(client, "query-running")

    assert mock_sleep.call_count == 2
