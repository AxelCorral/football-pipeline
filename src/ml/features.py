"""
Accès au dataset de features produit par dbt.

Les moyennes glissantes ne sont plus calculées ici : elles le sont en SQL, par
``fct_match_features`` (voir ``dbt/models/marts/ml/``). Ce module ne fait que
charger le mart, en tirer la matrice attendue par les modèles entraînés, et
composer une ligne de features pour une affiche que le calendrier ne contient
pas encore.

Ce partage est volontaire. Une fenêtre glissante par équipe, par saison et par
contexte est un exercice de SQL analytique, et l'écrire deux fois — une fois en
pandas pour l'entraînement, une fois ailleurs pour le service — est le meilleur
moyen d'obtenir deux définitions divergentes de la même feature.
"""

from pathlib import Path

import pandas as pd

from src.marts import FCT_MATCH_FEATURES, MART_TEAM_FORM, MARTS_DIR, read_mart

# Les sept entrées des modèles versionnés dans models/. L'ordre compte : c'est
# celui dans lequel les colonnes ont été présentées à scikit-learn.
FEATURE_COLS = [
    "home_form",
    "away_form",
    "home_goals_avg",
    "away_goals_avg",
    "home_conceded_avg",
    "away_conceded_avg",
    "home_advantage",
]

# Feature du modèle → colonne du mart. Toutes décrivent le contexte du match à
# venir : ce que le receveur fait à domicile, ce que le visiteur fait dehors.
FEATURE_SOURCE: dict[str, str] = {
    "home_form": "home_home_avg_points_last_5",
    "away_form": "away_away_avg_points_last_5",
    "home_goals_avg": "home_home_avg_goals_for_last_5",
    "away_goals_avg": "away_away_avg_goals_for_last_5",
    "home_conceded_avg": "home_home_avg_goals_against_last_5",
    "away_conceded_avg": "away_away_avg_goals_against_last_5",
}

# Le modèle prédit toujours une rencontre avec un receveur : la colonne est
# constante par construction. Elle est conservée parce que les modèles
# versionnés attendent sept entrées.
HOME_ADVANTAGE = 1

TARGET_COL = "target_result"


def load_match_features(marts_dir: Path | str = MARTS_DIR) -> pd.DataFrame:
    """Charge ``fct_match_features`` depuis l'export Parquet des marts.

    Args:
        marts_dir: Répertoire écrit par ``scripts/export_marts.py``.

    Returns:
        Le mart, trié par ``(match_date, match_id)``. Ce tri total et
        déterministe est ce sur quoi repose le découpage temporel : deux
        rencontres au même coup d'envoi doivent tomber du même côté du split
        d'une exécution à l'autre.

    Raises:
        FileNotFoundError: Le mart n'a pas été exporté.
    """
    return read_mart(FCT_MATCH_FEATURES, marts_dir).sort_values(
        ["match_date", "match_id"], kind="stable"
    )


def load_team_form(marts_dir: Path | str = MARTS_DIR) -> pd.DataFrame:
    """Charge ``mart_team_form`` : bilan de saison et forme récente par équipe."""
    return read_mart(MART_TEAM_FORM, marts_dir)


def add_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes ``FEATURE_COLS`` à partir des colonnes du mart.

    Args:
        df: Lignes de ``fct_match_features``.

    Returns:
        Une copie de ``df`` avec les sept colonnes attendues par les modèles.
        Les valeurs manquantes du mart — équipe sans historique — restent NaN.
    """
    out = df.copy()
    for feature, source in FEATURE_SOURCE.items():
        out[feature] = pd.to_numeric(out[source], errors="coerce")
    out["home_advantage"] = HOME_ADVANTAGE
    return out


def training_frame(
    df: pd.DataFrame,
    competition_code: str | None = None,
) -> pd.DataFrame:
    """Restreint le mart aux lignes entraînables, dans l'ordre chronologique.

    Une ligne est entraînable si le match a été joué — donc si la cible existe —
    et si les sept features sont disponibles. Les premières journées et les
    promus n'ont pas d'historique : leurs features sont NULL dans le mart, et
    elles sont écartées ici plutôt qu'imputées à zéro, qui se confondrait avec
    « a joué et n'a rien pris ».

    Args:
        df: Lignes de ``fct_match_features``.
        competition_code: Restreint à une compétition ; toutes si None.

    Returns:
        DataFrame trié par date, avec ``FEATURE_COLS`` et ``target_result``.
    """
    frame = df
    if competition_code is not None:
        frame = frame[frame["competition_code"] == competition_code]

    frame = add_feature_columns(frame)
    frame = frame[frame[TARGET_COL].notna()]
    frame = frame.dropna(subset=FEATURE_COLS)
    return frame.sort_values(["match_date", "match_id"], kind="stable")


def fixture_features(
    team_form: pd.DataFrame,
    home_team: str,
    away_team: str,
) -> pd.DataFrame | None:
    """Compose une ligne de features pour une affiche arbitraire.

    Sert la page Prediction du dashboard, qui laisse choisir deux équipes sans
    que la rencontre existe au calendrier. La forme retenue est la plus récente
    connue de chaque équipe — celle qui suit son dernier match joué dans le
    contexte concerné.

    Args:
        team_form: Lignes de ``mart_team_form``.
        home_team: Équipe qui reçoit.
        away_team: Équipe qui se déplace.

    Returns:
        DataFrame d'une ligne contenant ``FEATURE_COLS``, ou None si l'une des
        deux équipes n'a pas encore de forme dans le contexte demandé.
    """
    home = team_form[team_form["team"] == home_team]
    away = team_form[team_form["team"] == away_team]
    if home.empty or away.empty:
        return None

    home_row = home.iloc[0]
    away_row = away.iloc[0]

    values = {
        "home_form": home_row["home_form_avg_points"],
        "away_form": away_row["away_form_avg_points"],
        "home_goals_avg": home_row["home_form_avg_goals_for"],
        "away_goals_avg": away_row["away_form_avg_goals_for"],
        "home_conceded_avg": home_row["home_form_avg_goals_against"],
        "away_conceded_avg": away_row["away_form_avg_goals_against"],
        "home_advantage": HOME_ADVANTAGE,
    }
    if any(pd.isna(v) for v in values.values()):
        return None

    return pd.DataFrame([values])[FEATURE_COLS]
