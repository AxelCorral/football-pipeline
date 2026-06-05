"""
Ingestion complète : 5 compétitions européennes, saisons 2024 et 2025.

Usage :
    python scripts/ingest_all.py
    python scripts/ingest_all.py --season 2025   # une seule saison

Le paramètre season est transmis à l'API ; en free tier une réponse 400
déclenche le fallback automatique (saison courante).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config  # noqa: E402
from src.ingestion.fetch_matches import (  # noqa: E402
    COMPETITION_NAMES,
    fetch_all_competitions,
    upload_to_s3,
)
from src.transform.process_matches import (  # noqa: E402
    build_curated_key,
    load_raw_from_s3,
    save_as_parquet,
    transform,
)

COMPETITIONS = ["PL", "FL1", "BL1", "SA", "PD"]
SEASONS = [2024, 2025]


def ingest_season(season: int, cfg: Config) -> dict[str, int]:
    """Ingère et transforme les 5 compétitions pour une saison donnée."""
    print(f"\n{'='*60}")
    print(f"Ingestion — {len(COMPETITIONS)} compétitions — saison {season}")
    print(f"{'='*60}")

    all_results = fetch_all_competitions(COMPETITIONS, season=season, config=cfg)

    for code, matches in all_results.items():
        if matches:
            uri = upload_to_s3(matches, cfg.aws_bucket_name, code, config=cfg)
            print(f"  ✓ {code}: {len(matches)} matchs → {uri}")
        else:
            print(f"  ✗ {code}: aucun match récupéré")

    print(f"\n--- Transformation → Parquet curated/ (saison {season}) ---")
    summary: dict[str, int] = {}
    for code in COMPETITIONS:
        df_raw = load_raw_from_s3(cfg.aws_bucket_name, code, config=cfg)
        if df_raw.empty:
            print(f"  ✗ {code}: données S3 vides")
            summary[code] = 0
            continue
        df = transform(df_raw)
        key = build_curated_key(code, season)
        uri = save_as_parquet(df, cfg.aws_bucket_name, key, config=cfg)
        n_fin = int((df["status"] == "FINISHED").sum())
        print(f"  ✓ {code}: {len(df)} matchs ({n_fin} terminés) → {uri}")
        summary[code] = len(df)

    return summary


def main(seasons: list[int]) -> None:
    cfg = Config()
    if not cfg.aws_bucket_name:
        print("Erreur : AWS_BUCKET_NAME non défini dans .env", file=sys.stderr)
        sys.exit(1)

    grand_summary: dict[str, dict[int, int]] = {c: {} for c in COMPETITIONS}
    for season in seasons:
        summary = ingest_season(season, cfg)
        for code, n in summary.items():
            grand_summary[code][season] = n

    print(f"\n{'='*60}")
    print("Récapitulatif global")
    print(f"{'='*60}")
    header = f"  {'Code':<5}  {'Compétition':<25}" + "".join(f"  {s}" for s in seasons)
    print(header)
    print(f"  {'-'*5}  {'-'*25}" + "  ----" * len(seasons))
    for code in COMPETITIONS:
        name = COMPETITION_NAMES.get(code, code)
        row = f"  {code:<5}  {name:<25}"
        for season in seasons:
            row += f"  {grand_summary[code].get(season, 0):>4}"
        print(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion multi-compétitions")
    parser.add_argument(
        "--season",
        type=int,
        default=None,
        help="Saison unique (ex: 2025). Sans argument : 2024 et 2025.",
    )
    args = parser.parse_args()
    target_seasons = [args.season] if args.season else SEASONS
    main(seasons=target_seasons)
