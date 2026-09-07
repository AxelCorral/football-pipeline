"""
Les marts dbt, côté Python.

``scripts/export_marts.py`` écrit ces fichiers depuis Athena ou depuis un build
dbt local ; tout ce qui les lit passe par ici. Un seul endroit sait donc où ils
se trouvent, quels noms ils portent, et quoi dire quand ils manquent — le
dashboard déployé n'a aucun accès AWS et ne voit du pipeline que ces Parquet.
"""

from pathlib import Path

import pandas as pd

MARTS_DIR = Path("data/marts")

FCT_MATCH_FEATURES = "fct_match_features"
MART_TEAM_FORM = "mart_team_form"
MART_LEAGUE_OVERVIEW = "mart_league_overview"
MART_MATCHWEEK_GOALS = "mart_matchweek_goals"

# Les marts exportés, dans l'ordre où ils sont écrits.
EXPORTED: tuple[str, ...] = (
    FCT_MATCH_FEATURES,
    MART_TEAM_FORM,
    MART_LEAGUE_OVERVIEW,
    MART_MATCHWEEK_GOALS,
)

_REBUILD_HINT = (
    "lancer `dbt build --project-dir dbt --target dev` puis "
    "`python scripts/export_marts.py --source duckdb`"
)


def mart_path(name: str, marts_dir: Path | str = MARTS_DIR) -> Path:
    """Chemin du Parquet d'un mart."""
    return Path(marts_dir) / f"{name}.parquet"


def read_mart(name: str, marts_dir: Path | str = MARTS_DIR) -> pd.DataFrame:
    """Lit un mart exporté.

    Args:
        name: Nom du modèle dbt (voir les constantes du module).
        marts_dir: Répertoire des exports ; ``data/marts`` par défaut.

    Returns:
        Le mart tel qu'exporté.

    Raises:
        FileNotFoundError: Le mart n'a pas été exporté, avec la commande à lancer.
    """
    path = mart_path(name, marts_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} est absent — {_REBUILD_HINT}.")
    return pd.read_parquet(path)
