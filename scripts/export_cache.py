"""
Export des données S3 vers le cache local pour l'app Streamlit.

Lit les JSON bruts depuis raw/{code}/ pour chaque compétition, les transforme
et les sauvegarde individuellement puis concaténés dans data/cache/.

Usage :
    python scripts/export_cache.py              # saison 2025 (défaut)
    python scripts/export_cache.py --season 2024

Sorties :
    data/cache/matches_{CODE}_{season}.parquet  (un fichier par compétition)
    data/cache/matches_all_{season}.parquet     (toutes compétitions réunies)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config  # noqa: E402
from src.transform.process_matches import load_raw_from_s3, transform  # noqa: E402

COMPETITIONS = ["PL", "FL1", "BL1", "SA", "PD"]
COMPETITION_NAMES = {
    "PL": "Premier League",
    "FL1": "Ligue 1",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "PD": "Primera Division",
}
CACHE_DIR = Path("data/cache")


def main(season: int = 2025) -> None:
    cfg = Config()
    if not cfg.aws_bucket_name:
        print("Erreur : AWS_BUCKET_NAME non défini dans .env", file=sys.stderr)
        sys.exit(1)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    all_dfs: list[pd.DataFrame] = []

    print(f"Export S3 → cache local (saison {season})\n")
    for code in COMPETITIONS:
        name = COMPETITION_NAMES.get(code, code)
        print(f"[{code}] {name}")
        print(f"  Lecture s3://{cfg.aws_bucket_name}/raw/{code}/ ...")
        df_raw = load_raw_from_s3(cfg.aws_bucket_name, code, config=cfg)
        if df_raw.empty:
            print("  ✗ Aucune donnée disponible sur S3\n")
            continue

        df = transform(df_raw)
        df["league_code"] = code
        n_fin = int((df["status"] == "FINISHED").sum())
        print(f"  ✓ {len(df)} matchs ({n_fin} terminés)")

        out_path = CACHE_DIR / f"matches_{code}_{season}.parquet"
        df.to_parquet(out_path, index=False, engine="pyarrow")
        print(f"  → {out_path}\n")
        all_dfs.append(df)

    if not all_dfs:
        print(
            "Erreur : aucune donnée récupérée pour aucune compétition.", file=sys.stderr
        )
        sys.exit(1)

    combined = pd.concat(all_dfs, ignore_index=True)
    combined_path = CACHE_DIR / f"matches_all_{season}.parquet"
    combined.to_parquet(combined_path, index=False, engine="pyarrow")

    n_fin_total = int((combined["status"] == "FINISHED").sum())
    leagues = combined["league_code"].nunique()
    print(
        f"Cache global : {len(combined)} matchs · {n_fin_total} terminés"
        f" · {leagues} compétitions → {combined_path}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2025)
    args = parser.parse_args()
    main(season=args.season)
