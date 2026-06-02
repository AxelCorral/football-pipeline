"""
Transformation des matchs bruts S3 en DataFrame Parquet normalisé.

Pipeline :
  1. load_raw_from_s3 — lit et concatène les JSON bruts depuis S3
  2. transform         — normalise, extrait et calcule les colonnes cibles
  3. save_as_parquet   — sérialise en Parquet et uploade dans curated/

Schéma curated : curated/{competition_code}/{season}/matches.parquet
"""
import io
import json
from typing import Any

import boto3
import pandas as pd

from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)

_OUTPUT_COLUMNS = [
    "match_id",
    "date",
    "competition",
    "competition_code",
    "season",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "total_goals",
    "result",
    "status",
    "referee",
    "venue",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_raw_from_s3(
    bucket: str,
    competition_code: str,
    *,
    config: Config | None = None,
) -> pd.DataFrame:
    """Lit tous les fichiers JSON sous ``raw/{competition_code}/`` et les concatène.

    Chaque fichier JSON doit contenir une liste de matchs (format produit
    par src.ingestion.fetch_matches.upload_to_s3).

    Args:
        bucket: Nom du bucket S3.
        competition_code: Code de la compétition (ex : ``"PL"``).
                          Le préfixe S3 utilisé sera ``raw/{competition_code}/``.
        config: Configuration du pipeline ; ``Config()`` si None.

    Returns:
        DataFrame aplati (``pd.json_normalize``) ; vide si aucun fichier.
    """
    if config is None:
        config = Config()

    prefix = f"raw/{competition_code}/"
    s3 = boto3.client("s3", region_name=config.aws_region)
    all_matches: list[dict[str, Any]] = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                logger.debug("Fichier ignoré (non-JSON) : %s", key)
                continue
            logger.info("Lecture s3://%s/%s", bucket, key)
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            data = json.loads(body)
            if isinstance(data, list):
                all_matches.extend(data)
            else:
                logger.warning("Format inattendu dans %s (attendu list, reçu %s)", key, type(data).__name__)

    if not all_matches:
        logger.warning("Aucun match trouvé sous s3://%s/%s", bucket, prefix)
        return pd.DataFrame()

    logger.info("%d matchs chargés depuis s3://%s/%s", len(all_matches), bucket, prefix)
    return pd.json_normalize(all_matches)


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise le DataFrame brut en forme analytique prête pour Parquet.

    Entrée attendue : DataFrame issu de ``pd.json_normalize``, avec des
    colonnes pointées telles que ``homeTeam.name``, ``score.fullTime.home``.

    Colonnes produites : voir ``_OUTPUT_COLUMNS``.  Les colonnes numériques
    (buts) utilisent le type ``Int64`` (nullable) afin de représenter
    correctement les matchs non encore joués.

    Args:
        df: DataFrame brut (sortie de ``load_raw_from_s3``).

    Returns:
        DataFrame normalisé avec types corrects.
    """
    if df.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    out = pd.DataFrame(index=df.index)

    out["match_id"] = pd.to_numeric(_col(df, "id"), errors="coerce").astype("Int64")
    out["date"] = pd.to_datetime(_col(df, "utcDate"), utc=True, errors="coerce")
    out["competition"] = _col(df, "competition.name")
    out["competition_code"] = _col(df, "competition.code")
    out["season"] = pd.to_numeric(
        _col(df, "season.startDate").astype(str).str[:4], errors="coerce"
    ).astype("Int64")
    out["home_team"] = _col(df, "homeTeam.name")
    out["away_team"] = _col(df, "awayTeam.name")
    out["home_goals"] = pd.to_numeric(
        _col(df, "score.fullTime.home"), errors="coerce"
    ).astype("Int64")
    out["away_goals"] = pd.to_numeric(
        _col(df, "score.fullTime.away"), errors="coerce"
    ).astype("Int64")
    # Addition de deux Int64 : NA se propage correctement via la conversion float
    out["total_goals"] = (
        out["home_goals"].astype(float) + out["away_goals"].astype(float)
    ).astype("Int64")
    out["result"] = _compute_result(out["home_goals"], out["away_goals"])
    out["status"] = _col(df, "status")
    out["referee"] = _extract_referee(df)
    out["venue"] = _col(df, "venue")

    logger.info(
        "Transform : %d lignes (%d avec score, %d sans)",
        len(out),
        out["home_goals"].notna().sum(),
        out["home_goals"].isna().sum(),
    )
    return out


def build_curated_key(competition_code: str, season: int | str) -> str:
    """Construit la clé S3 pour les données curées.

    Format : ``curated/{competition_code}/{season}/matches.parquet``
    """
    return f"curated/{competition_code}/{season}/matches.parquet"


def save_as_parquet(
    df: pd.DataFrame,
    bucket: str,
    key: str,
    *,
    config: Config | None = None,
) -> str:
    """Sérialise le DataFrame en Parquet et l'uploade sur S3.

    Args:
        df: DataFrame à persister (doit être non-vide).
        bucket: Nom du bucket S3.
        key: Clé S3 cible (ex : ``"curated/PL/2023/matches.parquet"``).
        config: Configuration du pipeline ; ``Config.load()`` si None.

    Returns:
        URI S3 complète : ``s3://{bucket}/{key}``.

    Raises:
        ValueError: Si ``df`` est vide.
    """
    if df.empty:
        raise ValueError("Impossible de sauvegarder un DataFrame vide")

    if config is None:
        config = Config()

    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    buf.seek(0)
    payload = buf.read()

    s3 = boto3.client("s3", region_name=config.aws_region)
    logger.info(
        "Upload Parquet s3://%s/%s (%d octets, %d lignes)",
        bucket,
        key,
        len(payload),
        len(df),
    )
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload,
        ContentType="application/octet-stream",
    )

    uri = f"s3://{bucket}/{key}"
    logger.info("Parquet écrit : %s", uri)
    return uri


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Retourne la colonne si présente, sinon une série de None alignée."""
    if name in df.columns:
        return df[name]
    return pd.Series(None, index=df.index, dtype=object)


def _compute_result(home: pd.Series, away: pd.Series) -> pd.Series:
    """Calcule H / A / D selon les buts. None si score absent."""
    result = pd.Series(None, index=home.index, dtype=object)
    scored = home.notna() & away.notna()
    # Conversion float : pd.NA → NaN ; comparaison NaN → False (numpy)
    h = home.astype(float)
    a = away.astype(float)
    result.loc[scored & (h > a)] = "H"
    result.loc[scored & (a > h)] = "A"
    result.loc[scored & (h == a)] = "D"
    return result


def _extract_referee(df: pd.DataFrame) -> pd.Series:
    """Extrait le nom du premier arbitre depuis la colonne ``referees`` (liste)."""
    if "referees" not in df.columns:
        return pd.Series(None, index=df.index, dtype=object)

    def _first(referees: Any) -> str | None:
        if not isinstance(referees, list) or not referees:
            return None
        entry = referees[0]
        return entry.get("name") if isinstance(entry, dict) else None

    return df["referees"].apply(_first)
