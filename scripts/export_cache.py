"""
Export des données S3 vers le cache local pour l'app Streamlit.

Usage :
    python scripts/export_cache.py

Prérequis : credentials AWS valides + variables d'environnement dans .env
    AWS_BUCKET_NAME, AWS_REGION

Sortie :
    data/cache/matches_PL_2025.parquet
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.transform.process_matches import load_raw_from_s3, transform

OUTPUT_PATH = Path("data/cache/matches_PL_2025.parquet")


def main() -> None:
    cfg = Config()
    if not cfg.aws_bucket_name:
        print("Erreur : AWS_BUCKET_NAME non défini dans .env", file=sys.stderr)
        sys.exit(1)

    print(f"Lecture depuis s3://{cfg.aws_bucket_name}/raw/PL/ ...")
    df_raw = load_raw_from_s3(cfg.aws_bucket_name, "PL", config=cfg)

    if df_raw.empty:
        print("Aucun match trouvé sur S3.", file=sys.stderr)
        sys.exit(1)

    df = transform(df_raw)
    finished = df[df["status"] == "FINISHED"]
    print(f"{len(df)} matchs transformés ({len(finished)} terminés).")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False, engine="pyarrow")
    print(f"Cache sauvegardé : {OUTPUT_PATH}")
    print(f"Colonnes : {list(df.columns)}")


if __name__ == "__main__":
    main()
