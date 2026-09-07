"""
Métriques d'évaluation : baseline naïve, log loss et score de Brier.

L'accuracy seule ne dit pas grand-chose d'un problème à trois issues dont la
distribution est déséquilibrée : un modèle qui prédit toujours la victoire à
domicile atteint déjà ~44 %. Les deux métriques probabilistes disent, elles,
si le modèle est calibré — s'il a raison d'être sûr quand il l'est.
"""

import numpy as np
import pandas as pd

# Ordre des classes utilisé par tout le projet : voir src.ml.train.LABEL_MAP.
LABELS = ["H", "D", "A"]


def baseline_accuracy(df: pd.DataFrame, target_col: str = "target_result") -> float:
    """Accuracy d'un classificateur naïf qui prédit toujours H.

    Args:
        df: DataFrame contenant la colonne cible (``fct_match_features``).
        target_col: Nom de la colonne cible.

    Returns:
        Fraction de matchs joués remportés à domicile. 0.0 si aucun match.
    """
    if target_col not in df.columns:
        return 0.0
    played = df[df[target_col].notna()]
    if played.empty:
        return 0.0
    return float((played[target_col] == "H").mean())


def log_loss_score(y_true: np.ndarray, proba: np.ndarray) -> float:
    """Log loss multiclasse, classes ordonnées comme ``LABELS``.

    Args:
        y_true: Indices de classe réels (0=H, 1=D, 2=A).
        proba: Probabilités prédites, une colonne par classe.

    Returns:
        Log loss ; plus bas est meilleur. Une prédiction uniforme vaut ln(3).
    """
    from sklearn.metrics import log_loss

    return float(log_loss(y_true, proba, labels=[0, 1, 2]))


def brier_score(y_true: np.ndarray, proba: np.ndarray) -> float:
    """Score de Brier multiclasse (erreur quadratique sur les probabilités).

    Args:
        y_true: Indices de classe réels (0=H, 1=D, 2=A).
        proba: Probabilités prédites, une colonne par classe.

    Returns:
        Moyenne des ``sum((p - onehot)^2)`` ; plus bas est meilleur, 0 est parfait.
    """
    onehot = np.zeros_like(proba, dtype=float)
    onehot[np.arange(len(y_true)), np.asarray(y_true, dtype=int)] = 1.0
    return float(np.mean(np.sum((proba - onehot) ** 2, axis=1)))
