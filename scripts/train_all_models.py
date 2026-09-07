"""
Entraîne un modèle par ligue (PL, FL1, BL1, SA, PD) + un modèle global "all",
en réutilisant la logique d'entraînement de src/ml/train.py.

Lit le mart dbt exporté par ``scripts/export_marts.py`` — plus aucun calcul de
feature ici — et sauvegarde un .joblib par compétition ainsi qu'un fichier de
métriques agrégé.

Usage :
    dbt build --project-dir dbt --target dev
    python scripts/export_marts.py --source duckdb
    python scripts/train_all_models.py

Sorties :
    models/match_predictor_{league}.joblib  (un par ligue + "all")
    models/metrics.json                     (accuracy, log loss, Brier, etc.)
"""

import json
import logging
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ml.evaluate import baseline_accuracy  # noqa: E402
from src.ml.features import load_match_features, training_frame  # noqa: E402
from src.ml.train import train_model_with_metrics  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

MODELS_DIR = ROOT / "models"

LEAGUES: tuple[str, ...] = ("PL", "FL1", "BL1", "SA", "PD", "all")


def _train_one(league: str, mart: pd.DataFrame) -> dict | None:
    """Entraîne et sauvegarde le modèle d'une ligue, retourne ses métriques."""
    competition = None if league == "all" else league
    frame = training_frame(mart, competition_code=competition)
    if frame.empty:
        logger.warning("Aucune ligne exploitable pour %s — ignoré", league)
        return None

    # Baseline mesurée sur tous les matchs joués de la ligue, features
    # disponibles ou non : c'est la définition utilisée depuis le début du
    # projet, conservée pour que les comparaisons restent lisibles.
    scope = mart if competition is None else mart[mart["competition_code"] == league]
    baseline = baseline_accuracy(scope)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            _model, metrics, _cm = train_model_with_metrics(frame, models_dir=tmp_dir)
        except ValueError as exc:
            logger.warning("Entraînement impossible pour %s : %s", league, exc)
            return None

        generated = list(tmp_dir.glob("*_match_predictor.joblib"))
        if not generated:
            logger.warning("Aucun fichier modèle généré pour %s", league)
            return None

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        target = MODELS_DIR / f"match_predictor_{league}.joblib"
        shutil.move(str(generated[0]), str(target))

    logger.info(
        "%s : modèle=%s accuracy=%.3f baseline=%.3f gain=%+.3f "
        "log_loss=%.3f brier=%.3f (n=%d) -> %s",
        league,
        metrics["model"],
        metrics["accuracy"],
        baseline,
        metrics["accuracy"] - baseline,
        metrics["log_loss"],
        metrics["brier"],
        len(frame),
        target,
    )

    return {
        "accuracy": metrics["accuracy"],
        "baseline": baseline,
        "gain": metrics["accuracy"] - baseline,
        "log_loss": metrics["log_loss"],
        "brier": metrics["brier"],
        "model": metrics["model"],
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": len(frame),
        "n_train": metrics["n_train"],
        "n_test": metrics["n_test"],
    }


def main() -> None:
    try:
        mart = load_match_features(ROOT / "data" / "marts")
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    metrics: dict[str, dict] = {}
    for league in LEAGUES:
        result = _train_one(league, mart)
        if result is not None:
            metrics[league] = result

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = MODELS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    logger.info("Métriques écrites dans %s", metrics_path)


if __name__ == "__main__":
    main()
