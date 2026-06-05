"""
Calcul des features pour la prédiction du résultat d'un match.

Pour chaque match FINISHED, calcule des statistiques de forme glissantes
sur les 5 derniers matchs par équipe. Le shift(1) garantit qu'aucune
information du match courant ne fuite dans ses propres features.
"""

import pandas as pd

WINDOW = 5
FEATURE_COLS = [
    "home_form",
    "away_form",
    "home_goals_avg",
    "away_goals_avg",
    "home_conceded_avg",
    "away_conceded_avg",
    "home_advantage",
]


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les features de forme glissante pour les matchs FINISHED.

    Args:
        df: DataFrame produit par transform() (process_matches.py).
            Colonnes requises : date, status, result, home_team, away_team,
            home_goals, away_goals.

    Returns:
        DataFrame filtré sur FINISHED, trié par date, avec FEATURE_COLS ajoutées.
        Les premiers matchs d'une équipe peuvent avoir des NaN (historique vide).
    """
    finished = df[df["status"] == "FINISHED"].sort_values("date").copy()

    if finished.empty:
        for col in FEATURE_COLS:
            finished[col] = pd.Series(dtype=float)
        return finished

    def _roll(s: pd.Series) -> pd.Series:
        return s.shift(1).rolling(WINDOW, min_periods=1).mean()

    finished["_home_pts"] = finished["result"].map({"H": 3, "D": 1, "A": 0})
    finished["home_form"] = finished.groupby("home_team")["_home_pts"].transform(_roll)
    finished["home_goals_avg"] = finished.groupby("home_team")["home_goals"].transform(
        _roll
    )
    finished["home_conceded_avg"] = finished.groupby("home_team")[
        "away_goals"
    ].transform(_roll)

    finished["_away_pts"] = finished["result"].map({"A": 3, "D": 1, "H": 0})
    finished["away_form"] = finished.groupby("away_team")["_away_pts"].transform(_roll)
    finished["away_goals_avg"] = finished.groupby("away_team")["away_goals"].transform(
        _roll
    )
    finished["away_conceded_avg"] = finished.groupby("away_team")[
        "home_goals"
    ].transform(_roll)

    finished["home_advantage"] = 1

    return finished.drop(columns=["_home_pts", "_away_pts"])
