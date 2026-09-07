"""
Entraînement d'un classificateur pour prédire le résultat d'un match (H/D/A).

Les features viennent du mart dbt ``fct_match_features`` : ce module ne calcule
aucune statistique historique, il sélectionne des colonnes, découpe dans le
temps, entraîne et évalue.

Split temporel 80/20 sans shuffle pour respecter l'ordre chronologique.
Le meilleur modèle (LogisticRegression vs RandomForest) est sauvegardé en joblib.
"""

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix

from src.ml.evaluate import brier_score, log_loss_score
from src.ml.features import FEATURE_COLS, TARGET_COL

logger = logging.getLogger(__name__)

MODELS_DIR = Path("models")
LABEL_MAP = {"H": 0, "D": 1, "A": 2}


def train_model(
    df_features: pd.DataFrame,
    models_dir: Path = MODELS_DIR,
) -> tuple[Any, float, np.ndarray]:
    """Entraîne LR et RF, retourne le meilleur modèle, accuracy et matrice de confusion.

    Args:
        df_features: Sortie de ``src.ml.features.training_frame()`` — les
            colonnes FEATURE_COLS et la cible, triées chronologiquement.
        models_dir: Répertoire de sauvegarde du modèle (.joblib).

    Returns:
        (best_model, accuracy_test, confusion_matrix) — labels [H=0, D=1, A=2].

    Raises:
        ValueError: Moins de 10 lignes valides après suppression des NaN.
    """
    _model, metrics, cm = train_model_with_metrics(df_features, models_dir)
    return _model, metrics["accuracy"], cm


def train_model_with_metrics(
    df_features: pd.DataFrame,
    models_dir: Path = MODELS_DIR,
) -> tuple[Any, dict[str, Any], np.ndarray]:
    """Comme ``train_model``, mais retourne aussi log loss et score de Brier.

    Args:
        df_features: Lignes entraînables, triées chronologiquement.
        models_dir: Répertoire de sauvegarde du modèle (.joblib).

    Returns:
        (best_model, metrics, confusion_matrix). ``metrics`` contient
        ``model``, ``accuracy``, ``log_loss``, ``brier``, ``n_train``, ``n_test``.

    Raises:
        ValueError: Moins de 10 lignes valides après suppression des NaN.
    """
    clean = df_features.dropna(subset=FEATURE_COLS + [TARGET_COL]).copy()
    if len(clean) < 10:
        raise ValueError(
            f"Données insuffisantes : {len(clean)} lignes valides (minimum 10)"
        )

    X = clean[FEATURE_COLS].values.astype(float)
    y = clean[TARGET_COL].map(LABEL_MAP).values

    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=100, random_state=42),
    }

    best_model: Any = None
    best_acc = -1.0
    best_name = ""
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        logger.info("Modèle %s — accuracy test : %.3f", name, acc)
        if acc > best_acc:
            best_acc, best_model, best_name = acc, model, name

    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"{best_name}_match_predictor.joblib"
    joblib.dump(best_model, model_path)
    logger.info("Meilleur modèle : %s (%.3f) → %s", best_name, best_acc, model_path)

    proba = best_model.predict_proba(X_test)
    cm = confusion_matrix(y_test, best_model.predict(X_test), labels=[0, 1, 2])
    metrics = {
        "model": best_name,
        "accuracy": float(best_acc),
        "log_loss": log_loss_score(y_test, proba),
        "brier": brier_score(y_test, proba),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    return best_model, metrics, cm


if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    from src.ml.evaluate import baseline_accuracy
    from src.ml.features import load_match_features, training_frame

    try:
        mart = load_match_features()
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    frame = training_frame(mart, competition_code="PL")
    baseline = baseline_accuracy(frame)
    logger.info("Baseline naïve (toujours H) : %.3f", baseline)

    model, metrics, cm = train_model_with_metrics(frame)
    logger.info(
        "Accuracy %.3f | log loss %.3f | Brier %.3f | gain vs baseline %+.3f",
        metrics["accuracy"],
        metrics["log_loss"],
        metrics["brier"],
        metrics["accuracy"] - baseline,
    )
