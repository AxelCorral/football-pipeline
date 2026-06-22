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
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Les données à évaluer doivent être un DataFrame pandas")

    required_columns = {"status", "result"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colonnes requises absentes : {missing}")

    finished = df[df["status"] == "FINISHED"]
    if finished.empty:
        return 0.0

    invalid_results = finished.loc[~finished["result"].isin({"H", "D", "A"}), "result"]
    if not invalid_results.empty:
        labels = ", ".join(sorted({str(value) for value in invalid_results}))
        raise ValueError(f"Labels de résultat non supportés : {labels}")

    return float((finished["result"] == "H").mean())
