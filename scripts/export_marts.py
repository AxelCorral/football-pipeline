"""
Export des marts dbt vers ``data/marts/`` au format Parquet.

C'est le pont entre l'entrepôt et ce qui tourne sans credentials : le
dashboard Streamlit et l'entraînement ML lisent ces fichiers, jamais Athena
directement. Le déploiement Streamlit Community Cloud n'a aucun accès AWS.

Deux sources, mêmes tables, mêmes colonnes :

    python scripts/export_marts.py                  # Athena (production)
    python scripts/export_marts.py --source duckdb  # build dbt local / CI

La source ``duckdb`` lit le fichier produit par ``dbt build --target dev``.
Elle ne demande aucun credential et sert au développement comme à la CI.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Config  # noqa: E402
from src.marts import EXPORTED, mart_path  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

MARTS_DIR = ROOT / "data" / "marts"
DUCKDB_PATH = ROOT / "dbt" / "football_pipeline.duckdb"

# Les tables exportées viennent de src.marts : les couches staging et
# intermediate restent dans l'entrepôt, elles n'ont pas de consommateur hors dbt.
MARTS: tuple[str, ...] = EXPORTED


def read_from_duckdb(
    model: str,
    duckdb_path: Path = DUCKDB_PATH,
    schema: str = "main",
) -> pd.DataFrame:
    """Lit un modèle dbt depuis le fichier DuckDB produit par ``--target dev``."""
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        raise RuntimeError(
            "duckdb n'est pas installé — `pip install -r requirements-dev.txt`, "
            "ou exporter depuis Athena avec --source athena."
        ) from exc

    if not duckdb_path.exists():
        raise FileNotFoundError(
            f"{duckdb_path} est absent — lancer d'abord "
            "`dbt build --project-dir dbt --target dev`."
        )

    with duckdb.connect(str(duckdb_path), read_only=True) as con:
        return con.sql(f'select * from "{schema}"."{model}"').df()


def read_from_athena(
    model: str,
    *,
    config: Config | None = None,
    schema: str | None = None,
) -> pd.DataFrame:
    """Lit un modèle dbt depuis le schéma Athena dans lequel dbt l'a matérialisé."""
    from src.analytics.athena_queries import results_to_dataframe, run_athena_query

    if config is None:
        config = Config()
    schema = schema or config.dbt_athena_schema

    qeid = run_athena_query(
        f'SELECT * FROM "{schema}"."{model}"',
        schema,
        config.athena_output_s3,
        config=config,
    )
    return results_to_dataframe(qeid, config=config, coerce_types=True)


def export(
    source: str,
    *,
    marts_dir: Path = MARTS_DIR,
    duckdb_path: Path = DUCKDB_PATH,
    schema: str | None = None,
) -> dict[str, int]:
    """Exporte chaque mart en Parquet. Retourne ``{modèle: nombre de lignes}``."""
    marts_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}

    for model in MARTS:
        if source == "duckdb":
            df = read_from_duckdb(model, duckdb_path, schema or "main")
        else:
            df = read_from_athena(model, schema=schema)

        if df.empty:
            raise RuntimeError(
                f"{model} est vide — export interrompu plutôt que d'écraser "
                "le cache par un fichier sans données."
            )

        out = mart_path(model, marts_dir)
        df.to_parquet(out, index=False, engine="pyarrow")
        written[model] = len(df)
        logger.info("%s : %d lignes -> %s", model, len(df), out)

    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python scripts/export_marts.py",
        description="Export des marts dbt vers data/marts/ (Parquet).",
    )
    parser.add_argument(
        "--source",
        choices=["athena", "duckdb"],
        default="athena",
        help="Backend de lecture (défaut : athena).",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Schéma dbt cible ; DBT_ATHENA_SCHEMA ou 'main' selon la source.",
    )
    parser.add_argument(
        "--duckdb-path",
        type=Path,
        default=DUCKDB_PATH,
        help=f"Fichier DuckDB produit par dbt (défaut : {DUCKDB_PATH}).",
    )
    args = parser.parse_args(argv)

    written = export(
        args.source,
        duckdb_path=args.duckdb_path,
        schema=args.schema,
    )
    total = sum(written.values())
    logger.info(
        "Export terminé — %d tables, %d lignes : %s",
        len(written),
        total,
        ", ".join(f"{k}={v}" for k, v in written.items()),
    )


if __name__ == "__main__":
    main()
