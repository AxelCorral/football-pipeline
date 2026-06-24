"""
Couche d'inférence pour le dashboard — charge un modèle pré-entraîné et calcule
des probabilités de résultat (H/D/A). Aucune logique d'entraînement ici : le
modèle est produit hors-ligne par src/ml/train.py et chargé tel quel.
"""

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.ml.features import FEATURE_COLS

MODELS_DIR = Path("models")


def load_model(league: str) -> Any | None:
    """Charge le modèle pré-entraîné pour une ligue donnée.

    Args:
        league: Code de compétition (PL, FL1, BL1, SA, PD), ou "all" pour
            le modèle entraîné sur toutes les compétitions confondues.

    Returns:
        Le modèle chargé, ou None si le fichier .joblib correspondant
        n'existe pas (pas encore entraîné, ou pas encore déployé).
    """
    path = MODELS_DIR / f"match_predictor_{league}.joblib"
    if not path.exists():
        return None
    return joblib.load(path)


def predict_proba(model: Any, df_feat_row: pd.DataFrame) -> np.ndarray:
    """Calcule les probabilités H/D/A pour une ligne de features.

    Args:
        model: Modèle chargé via load_model().
        df_feat_row: DataFrame à une ligne contenant FEATURE_COLS.

    Returns:
        Array de probabilités [P(H), P(D), P(A)].
    """
    X = df_feat_row[FEATURE_COLS].values.astype(float)
    return model.predict_proba(X)[0]
