"""
Exécution de requêtes SQL sur AWS Athena et restitution en DataFrame.

Flux d'utilisation :
    qeid = run_athena_query(sql, database, output_s3)
    df   = results_to_dataframe(qeid)

Notes sur les types Athena :
  - Toutes les valeurs sont retournées en VarCharValue (chaîne).
  - La conversion de types (int, float, date) est à la charge de l'appelant.
  - Les cellules NULL sont représentées par un dict vide ``{}`` dans l'API
    boto3 ; elles sont converties en ``None`` dans le DataFrame résultant.
"""
import time

import boto3
import pandas as pd

from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 2
MAX_WAIT_SECONDS = 300

_TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_athena_query(
    query: str,
    database: str,
    output_s3: str,
    *,
    config: Config | None = None,
) -> str:
    """Soumet une requête Athena et bloque jusqu'à sa complétion.

    Polling toutes les ``POLL_INTERVAL_SECONDS`` secondes jusqu'à
    ``MAX_WAIT_SECONDS`` au maximum.

    Args:
        query: Instruction SQL à exécuter.
        database: Nom de la base de données Athena (catalogue Glue).
        output_s3: URI S3 de destination des résultats
                   (ex : ``"s3://bucket/athena-results/"``).
        config: Configuration du pipeline ; ``Config.load()`` si None.

    Returns:
        ``QueryExecutionId`` Athena (str).

    Raises:
        RuntimeError: La requête s'est terminée en état FAILED ou CANCELLED.
        TimeoutError: ``MAX_WAIT_SECONDS`` dépassés sans résultat.
    """
    if config is None:
        config = Config()

    client = boto3.client("athena", region_name=config.aws_region)

    logger.info("Soumission requête Athena — base : %s", database)
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": output_s3},
    )
    qeid: str = response["QueryExecutionId"]
    logger.info("QueryExecutionId : %s", qeid)

    _wait_for_completion(client, qeid)
    return qeid


def results_to_dataframe(
    query_execution_id: str,
    *,
    config: Config | None = None,
) -> pd.DataFrame:
    """Récupère les résultats d'une requête Athena terminée.

    Gère la pagination via ``NextToken``. La première ligne retournée par
    l'API Athena est toujours l'en-tête des colonnes ; elle est extraite
    et utilisée comme noms de colonnes du DataFrame.

    Args:
        query_execution_id: Identifiant retourné par ``run_athena_query``.
        config: Configuration du pipeline ; ``Config.load()`` si None.

    Returns:
        DataFrame dont toutes les colonnes sont de type ``object`` (str / None).
        Appeler ``pd.to_numeric``, ``pd.to_datetime``, etc. pour convertir.
    """
    if config is None:
        config = Config()

    client = boto3.client("athena", region_name=config.aws_region)

    columns: list[str] | None = None
    rows: list[list] = []
    next_token: str | None = None

    while True:
        kwargs: dict = {
            "QueryExecutionId": query_execution_id,
            "MaxResults": 1000,
        }
        if next_token:
            kwargs["NextToken"] = next_token

        resp = client.get_query_results(**kwargs)
        result_rows = resp["ResultSet"]["Rows"]

        if columns is None:
            # Première page : la ligne 0 contient les noms de colonnes.
            columns = [
                cell.get("VarCharValue", "")
                for cell in result_rows[0]["Data"]
            ]
            result_rows = result_rows[1:]
            logger.info(
                "Colonnes Athena (%d) : %s",
                len(columns),
                ", ".join(columns),
            )

        for row in result_rows:
            # cell vide ({}) → NULL Athena → None dans le DataFrame
            rows.append([cell.get("VarCharValue") for cell in row["Data"]])

        next_token = resp.get("NextToken")
        if not next_token:
            break

    if not rows:
        logger.info("Requête %s : aucune ligne de données", query_execution_id[:8])
        return pd.DataFrame(columns=columns or [])

    df = pd.DataFrame(rows, columns=columns)
    logger.info(
        "results_to_dataframe : %d lignes, %d colonnes (id=%s)",
        len(df),
        len(df.columns),
        query_execution_id[:8],
    )
    return df


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------


def _wait_for_completion(client, query_execution_id: str) -> None:
    """Bloque jusqu'à SUCCEEDED ou lève une exception.

    Interroge ``get_query_execution`` toutes les ``POLL_INTERVAL_SECONDS``
    secondes jusqu'à atteindre un état terminal.
    """
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

        resp = client.get_query_execution(QueryExecutionId=query_execution_id)
        status = resp["QueryExecution"]["Status"]
        state: str = status["State"]

        logger.debug(
            "Athena [%s] : %s (%ds / %ds)",
            query_execution_id[:8],
            state,
            elapsed,
            MAX_WAIT_SECONDS,
        )

        if state == "SUCCEEDED":
            logger.info(
                "Requête %s terminée avec succès en %ds",
                query_execution_id[:8],
                elapsed,
            )
            return

        if state in _TERMINAL_STATES:
            reason = status.get("StateChangeReason", "(sans détail)")
            raise RuntimeError(
                f"Requête Athena {query_execution_id[:8]} "
                f"terminée en état {state} : {reason}"
            )

    raise TimeoutError(
        f"Requête Athena {query_execution_id[:8]} toujours en cours "
        f"après {MAX_WAIT_SECONDS}s — augmenter MAX_WAIT_SECONDS si nécessaire"
    )
