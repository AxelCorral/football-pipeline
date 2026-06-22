"""Exécution de requêtes AWS Athena et restitution en DataFrame."""

import logging
import time

import boto3
import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2
MAX_WAIT_SECONDS = 300
_FAILED_STATES = frozenset({"FAILED", "CANCELLED"})


class AthenaQueryRunner:
    """Lance des requêtes SQL sur Athena et retourne les résultats."""

    def __init__(self, settings: Config) -> None:
        athena_database = settings.athena_database.strip()
        if not athena_database:
            raise ValueError("Le nom de la base Athena ne peut pas être vide")
        athena_output_s3 = settings.athena_output_s3.strip()
        if not athena_output_s3:
            raise ValueError("L'emplacement S3 des résultats ne peut pas être vide")
        aws_region = settings.aws_region.strip()
        if not aws_region:
            raise ValueError("La région AWS ne peut pas être vide")

        self.settings = settings
        self.athena_database = athena_database
        self.athena_output_s3 = athena_output_s3
        self.client = boto3.client("athena", region_name=aws_region)

    def run_query(self, sql: str) -> pd.DataFrame:
        """Soumet une requête, attend sa réussite et retourne ses résultats."""
        if not sql.strip():
            raise ValueError("La requête SQL ne peut pas être vide")

        response = self.client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": self.athena_database},
            ResultConfiguration={"OutputLocation": self.athena_output_s3},
        )
        query_execution_id = response["QueryExecutionId"]
        self._wait_for_query(query_execution_id)
        return self._fetch_results(query_execution_id)

    def _wait_for_query(self, query_execution_id: str) -> None:
        """Attend un état terminal, avec délai maximal borné."""
        elapsed = 0
        while elapsed <= MAX_WAIT_SECONDS:
            response = self.client.get_query_execution(
                QueryExecutionId=query_execution_id
            )
            status = response["QueryExecution"]["Status"]
            state = status["State"]

            if state == "SUCCEEDED":
                return
            if state in _FAILED_STATES:
                reason = status.get("StateChangeReason", "raison inconnue")
                raise RuntimeError(
                    f"Requête Athena {query_execution_id} en échec "
                    f"({state}) : {reason}"
                )

            if elapsed == MAX_WAIT_SECONDS:
                break
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed = min(elapsed + POLL_INTERVAL_SECONDS, MAX_WAIT_SECONDS)

        raise TimeoutError(
            f"Requête Athena {query_execution_id} toujours en cours "
            f"après {MAX_WAIT_SECONDS}s"
        )

    def _fetch_results(self, query_execution_id: str) -> pd.DataFrame:
        """Récupère toutes les pages et convertit les valeurs NULL en ``None``."""
        columns: list[str] | None = None
        rows: list[list[str | None]] = []
        next_token: str | None = None

        while True:
            request = {"QueryExecutionId": query_execution_id, "MaxResults": 1000}
            if next_token is not None:
                request["NextToken"] = next_token

            response = self.client.get_query_results(**request)
            result_set = response.get("ResultSet", {})
            result_rows = result_set.get("Rows", [])

            if columns is None:
                column_info = result_set.get("ResultSetMetadata", {}).get(
                    "ColumnInfo", []
                )
                columns = [column["Name"] for column in column_info]

                if result_rows:
                    if not columns:
                        columns = [
                            cell.get("VarCharValue", "")
                            for cell in result_rows[0].get("Data", [])
                        ]
                    result_rows = result_rows[1:]

            for row in result_rows:
                values = [cell.get("VarCharValue") for cell in row.get("Data", [])]
                if columns is not None:
                    values = (values + [None] * len(columns))[: len(columns)]
                rows.append(values)

            next_token = response.get("NextToken")
            if next_token is None:
                break

        return pd.DataFrame(rows, columns=columns or None)
