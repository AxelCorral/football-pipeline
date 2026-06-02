"""
Ingestion des matchs depuis l'API football-data.org vers S3.

Endpoint : GET /competitions/{code}/matches?season={YYYY}
           Le paramètre season est optionnel. Certaines offres (free tier)
           ne le supportent pas et retournent un 400. Un fallback automatique
           émet un second appel sans ce paramètre sur réception d'un 400.
Schéma S3  : raw/{competition_code}/{YYYY-MM-DD}/matches.json
"""

import json
import time
from datetime import date
from typing import Any

import boto3
import requests

from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # délais : 2^1=2 s, 2^2=4 s

# Statuts HTTP qui déclenchent un retry (erreurs serveur + rate-limit)
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def get_matches(
    competition_code: str,
    season: int | None = None,
    *,
    config: Config | None = None,
) -> list[dict[str, Any]]:
    """Récupère les matchs d'une compétition, avec ou sans filtre saison.

    Si ``season`` est fourni il est inclus dans les query params. En cas de
    réponse 400 (le free tier de football-data.org ne supporte pas ce
    paramètre), un second appel est émis sans ``season`` — ce fallback ne
    consomme pas les 3 retries réservés aux erreurs transientes (5xx/réseau).

    Args:
        competition_code: Code de la compétition (ex : "PL", "BL1", "SA").
        season: Année de début de saison (ex : 2023 pour 2023/24).
                ``None`` par défaut — aucun filtre n'est envoyé.
        config: Configuration du pipeline ; ``Config.load()`` si None.

    Returns:
        Liste de matchs (dicts) tels que retournés par l'API.

    Raises:
        requests.HTTPError: Erreur 4xx non couverte par le fallback.
        RuntimeError: Tous les retries ont échoué (erreurs serveur/réseau).
    """
    if config is None:
        config = Config()

    url = f"{config.football_api_base_url}/competitions/{competition_code}/matches"
    headers = {"X-Auth-Token": config.api_key}
    params: dict[str, Any] = {"season": season} if season is not None else {}

    try:
        return _request_with_retry(url, headers, params)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 400 and season is not None:
            logger.warning(
                "400 avec season=%s sur %s — le free tier ne supporte pas ce filtre. "
                "Nouvel essai sans le paramètre season.",
                season,
                url,
            )
            return _request_with_retry(url, headers, {})
        raise


def _request_with_retry(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """GET avec retry x3 et backoff exponentiel sur erreurs transientes.

    Retryable : 429, 5xx, ConnectionError / Timeout.
    Non retryable : tout autre 4xx — levée immédiate sans retry.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        if attempt > 0:
            delay = _BACKOFF_BASE**attempt
            logger.warning(
                "Retry %d/%d sur %s — attente %ds",
                attempt,
                _MAX_RETRIES - 1,
                url,
                delay,
            )
            time.sleep(delay)

        try:
            logger.info("GET %s params=%s", url, params or "(aucun)")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            matches: list[dict[str, Any]] = response.json().get("matches", [])
            logger.info("%d matchs récupérés depuis %s", len(matches), url)
            return matches

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in _RETRYABLE_STATUSES:
                logger.error("Erreur HTTP %s sur %s (non retryable)", status, url)
                raise
            logger.warning(
                "Erreur HTTP %s sur %s (tentative %d)", status, url, attempt + 1
            )
            last_exc = exc

        except requests.RequestException as exc:
            logger.warning(
                "Erreur réseau sur %s (tentative %d) : %s", url, attempt + 1, exc
            )
            last_exc = exc

    raise RuntimeError(f"Échec après {_MAX_RETRIES} tentatives sur {url}") from last_exc


def build_s3_key(competition_code: str, run_date: date | None = None) -> str:
    """Construit la clé S3 pour les matchs bruts d'une journée.

    Format : raw/{competition_code}/{YYYY-MM-DD}/matches.json
    """
    if run_date is None:
        run_date = date.today()
    return f"raw/{competition_code}/{run_date.isoformat()}/matches.json"


def upload_to_s3(
    data: list[dict[str, Any]],
    bucket: str,
    competition_code: str,
    run_date: date | None = None,
    *,
    config: Config | None = None,
) -> str:
    """Sérialise les matchs en JSON et les uploade sur S3.

    La clé S3 est construite automatiquement via ``build_s3_key`` :
    ``raw/{competition_code}/{YYYY-MM-DD}/matches.json``.

    Args:
        data: Liste de matchs à persister.
        bucket: Nom du bucket S3 cible.
        competition_code: Code de la compétition (ex : ``"PL"``).
        run_date: Date de la collecte ; aujourd'hui si None.
        config: Configuration du pipeline ; ``Config()`` si None.

    Returns:
        URI S3 complète : ``s3://{bucket}/{key}``.
    """
    if config is None:
        config = Config()

    key = build_s3_key(competition_code, run_date)
    payload = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")

    s3_client = boto3.client("s3", region_name=config.aws_region)

    logger.info(
        "Upload S3 s3://%s/%s (%d octets, %d matchs)",
        bucket,
        key,
        len(payload),
        len(data),
    )
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload,
        ContentType="application/json",
    )

    uri = f"s3://{bucket}/{key}"
    logger.info("Upload terminé : %s", uri)
    return uri
