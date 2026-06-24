"""
Point d'entrée du pipeline ETL football.

Orchestre les quatre étapes du pipeline, pour chaque compétition :
  1. Extraction des matchs depuis l'API football-data.org
  2. Stockage brut sur S3 (zone raw/, JSON)
  3. Transformation des données (normalisation, enrichissement)
  4. Stockage transformé sur S3 (zone curated/, Parquet)

Une compétition en échec est journalisée puis ignorée — elle n'interrompt
pas le traitement des autres.

Usage :
    python -m src.main                      # pipeline complet (5 ligues)
    python -m src.main --competition PL     # une seule compétition
    python -m src.main --dry-run            # affiche les actions prévues,
                                             # sans appel API ni S3
"""

import argparse
from datetime import date

from src.config import Config
from src.ingestion.fetch_matches import (
    COMPETITION_NAMES,
    build_s3_key,
    fetch_all_competitions,
    upload_to_s3,
)
from src.transform.process_matches import (
    build_curated_key,
    load_raw_from_s3,
    save_as_parquet,
    transform,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _log_dry_run(config: Config, competitions: list[str], season: int | None) -> None:
    """Affiche les actions que le pipeline exécuterait, sans rien appeler."""
    if not config.api_key:
        logger.warning("[DRY RUN] API_KEY non configurée")
    if not config.aws_bucket_name:
        logger.warning("[DRY RUN] AWS_BUCKET_NAME non configuré")

    logger.info(
        "[DRY RUN] Config — bucket=%s région=%s api_key=%s saison=%s",
        config.aws_bucket_name or "(non défini)",
        config.aws_region,
        "***" if config.api_key else "(non défini)",
        season if season is not None else "(courante)",
    )

    bucket = config.aws_bucket_name or "<bucket>"
    run_date = date.today()
    for code in competitions:
        name = COMPETITION_NAMES.get(code, code)
        raw_key = build_s3_key(code, run_date)
        curated_key = build_curated_key(
            code, season if season is not None else "<saison>"
        )
        logger.info(
            "[DRY RUN] %s (%s) : fetch matches -> upload s3://%s/%s "
            "-> transform -> save s3://%s/%s",
            code,
            name,
            bucket,
            raw_key,
            bucket,
            curated_key,
        )
    logger.info("[DRY RUN] Terminé — aucun appel API ni S3 effectué.")


def run_pipeline(
    config: Config,
    competitions: list[str] | None = None,
    *,
    season: int | None = None,
    dry_run: bool = False,
) -> None:
    """Exécute le pipeline ETL complet : ingestion -> raw S3 -> curated S3.

    Pour chaque compétition : récupère les matchs depuis l'API, les
    sauvegarde en JSON brut (raw/), puis relit l'ensemble du brut S3,
    le transforme et le sauvegarde en Parquet (curated/), partitionné
    par saison. Une compétition en échec (fetch, upload, transform ou
    sauvegarde) est journalisée et ignorée — elle n'interrompt pas les
    autres.

    Args:
        config: Configuration du pipeline (bucket, clé API, région...).
        competitions: Codes de compétitions à traiter ; les 5 ligues
            connues (voir COMPETITION_NAMES) si None.
        season: Année de début de saison à transmettre à l'API ; saison
            courante si None.
        dry_run: Si True, n'effectue aucun appel API ni S3 — affiche
            uniquement les actions qui seraient exécutées.

    Raises:
        RuntimeError: AWS_BUCKET_NAME non configuré (hors dry-run).
    """
    competitions = competitions or list(COMPETITION_NAMES)

    if dry_run:
        _log_dry_run(config, competitions, season)
        return

    if not config.aws_bucket_name:
        raise RuntimeError("AWS_BUCKET_NAME non configuré — pipeline interrompu")

    bucket = config.aws_bucket_name
    logger.info(
        "Pipeline démarré — %d compétition(s) : %s",
        len(competitions),
        ", ".join(competitions),
    )

    raw_matches = fetch_all_competitions(competitions, season=season, config=config)

    succeeded: list[str] = []
    failed: list[str] = []
    for code in competitions:
        matches = raw_matches.get(code, [])
        if not matches:
            logger.warning("%s : aucun match récupéré — compétition ignorée", code)
            failed.append(code)
            continue

        try:
            logger.info("=== %s — upload raw S3 ===", code)
            upload_to_s3(matches, bucket, code, config=config)

            logger.info("=== %s — transformation ===", code)
            df_raw = load_raw_from_s3(bucket, code, config=config)
            df_curated = transform(df_raw)
            if df_curated.empty:
                logger.warning(
                    "%s : transform a produit un DataFrame vide — sauvegarde ignorée",
                    code,
                )
                failed.append(code)
                continue

            logger.info("=== %s — sauvegarde curated ===", code)
            for season_value in df_curated["season"].dropna().unique():
                season_df = df_curated[df_curated["season"] == season_value]
                key = build_curated_key(code, int(season_value))
                save_as_parquet(season_df, bucket, key, config=config)

            logger.info("=== %s — terminé ===", code)
            succeeded.append(code)
        except Exception as exc:
            logger.error("%s : échec du pipeline — %s", code, exc, exc_info=True)
            failed.append(code)

    logger.info(
        "Pipeline terminé — %d/%d compétition(s) en succès%s",
        len(succeeded),
        len(competitions),
        f" (échecs : {', '.join(failed)})" if failed else "",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Pipeline ETL football — ingestion, transformation, sauvegarde S3.",
    )
    parser.add_argument(
        "--competition",
        choices=sorted(COMPETITION_NAMES),
        help="Limiter le pipeline à une seule compétition (toutes par défaut).",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=None,
        help="Année de début de saison à transmettre à l'API (saison courante si omis).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les actions prévues sans appeler l'API ni S3 "
        "(aucun credential AWS requis).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    competitions = [args.competition] if args.competition else None
    run_pipeline(Config(), competitions, season=args.season, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
