"""
Entraînement d'un classificateur pour prédire le résultat d'un match (H/D/A).

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

logger = logging.getLogger(__name__)

MODELS_DIR = Path("models")
LABEL_MAP = {"H": 0, "D": 1, "A": 2}
FEATURE_COLS = [
    "home_form",
    "away_form",
    "home_goals_avg",
    "away_goals_avg",
    "home_conceded_avg",
    "away_conceded_avg",
    "home_advantage",
]


def train_model(
    df_features: pd.DataFrame,
    models_dir: Path = MODELS_DIR,
) -> tuple[Any, float, np.ndarray]:
    """Entraîne LR et RF, retourne le meilleur modèle, accuracy et matrice de confusion.

    Args:
        df_features: Sortie de compute_features(), avec FEATURE_COLS et "result".
        models_dir: Répertoire de sauvegarde du modèle (.joblib).

    Returns:
        (best_model, accuracy_test, confusion_matrix) — labels [H=0, D=1, A=2].

    Raises:
        ValueError: Moins de 10 lignes valides après suppression des NaN.
    """
    clean = df_features.dropna(subset=FEATURE_COLS + ["result"]).copy()
    if len(clean) < 10:
        raise ValueError(
            f"Données insuffisantes : {len(clean)} lignes valides (minimum 10)"
        )

    X = clean[FEATURE_COLS].values.astype(float)
    y = clean["result"].map(LABEL_MAP).values

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

    cm = confusion_matrix(y_test, best_model.predict(X_test), labels=[0, 1, 2])
    return best_model, best_acc, cm


if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    from src.config import Config
    from src.ml.evaluate import baseline_accuracy
    from src.ml.features import compute_features
    from src.transform.process_matches import load_raw_from_s3, transform

    cfg = Config()
    df_raw = load_raw_from_s3(cfg.aws_bucket_name, "PL", config=cfg)
    if df_raw.empty:
        logger.error("Aucune donnée brute disponible sur S3 — pipeline interrompu")
        sys.exit(1)

    df = transform(df_raw)
    df_feat = compute_features(df)
    baseline = baseline_accuracy(df)
    logger.info("Baseline naïve (toujours H) : %.3f", baseline)

    model, acc, cm = train_model(df_feat)
    logger.info(
        "Accuracy finale : %.3f  |  gain vs baseline : %+.3f", acc, acc - baseline
    )
