"""
Baseline naïve pour comparer les modèles ML.
"""

import pandas as pd


def baseline_accuracy(df: pd.DataFrame) -> float:
    """Accuracy d'un classificateur naïf qui prédit toujours H (victoire domicile).

    Args:
        df: DataFrame avec colonnes "status" et "result".

    Returns:
        Fraction de matchs FINISHED remportés à domicile. 0.0 si aucun match.
    """
    finished = df[df["status"] == "FINISHED"]
    if finished.empty:
        return 0.0
    return float((finished["result"] == "H").mean())
