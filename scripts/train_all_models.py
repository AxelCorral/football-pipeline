"""
Entraîne un modèle par ligue (PL, FL1, BL1, SA, PD) + un modèle global "all",
en réutilisant la logique d'entraînement de src/ml/train.py.

Lit les caches locaux produits par scripts/export_cache.py et sauvegarde un
.joblib par compétition ainsi qu'un fichier de métriques agrégé.

Usage :
    python scripts/train_all_models.py

Sorties :
    models/match_predictor_{league}.joblib  (un par ligue + "all")
    models/metrics.json                     (accuracy, baseline, gain, etc.)
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
from src.ml.features import FEATURE_COLS, compute_features  # noqa: E402
from src.ml.train import train_model  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = ROOT / "data" / "cache"
MODELS_DIR = ROOT / "models"

LEAGUES: dict[str, Path] = {
    "PL": CACHE_DIR / "matches_PL_2025.parquet",
    "FL1": CACHE_DIR / "matches_FL1_2025.parquet",
    "BL1": CACHE_DIR / "matches_BL1_2025.parquet",
    "SA": CACHE_DIR / "matches_SA_2025.parquet",
    "PD": CACHE_DIR / "matches_PD_2025.parquet",
    "all": CACHE_DIR / "matches_all_2025.parquet",
}


def _train_one(league: str, cache_path: Path) -> dict | None:
    """Entraîne et sauvegarde le modèle d'une ligue, retourne ses métriques."""
    if not cache_path.exists():
        logger.warning("Cache absent pour %s (%s) — ignoré", league, cache_path)
        return None

    df = pd.read_parquet(cache_path)
    df_feat = compute_features(df)
    baseline = baseline_accuracy(df)
    n_rows = len(df_feat.dropna(subset=FEATURE_COLS + ["result"]))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            model, acc, _cm = train_model(df_feat, models_dir=tmp_dir)
        except ValueError as exc:
            logger.warning("Entraînement impossible pour %s : %s", league, exc)
            return None

        generated = list(tmp_dir.glob("*_match_predictor.joblib"))
        if not generated:
            logger.warning("Aucun fichier modèle généré pour %s", league)
            return None
        model_name = generated[0].stem.removesuffix("_match_predictor")

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        target = MODELS_DIR / f"match_predictor_{league}.joblib"
        shutil.move(str(generated[0]), str(target))

    logger.info(
        "%s : modèle=%s accuracy=%.3f baseline=%.3f gain=%+.3f (n=%d) → %s",
        league,
        model_name,
        acc,
        baseline,
        acc - baseline,
        n_rows,
        target,
    )

    return {
        "accuracy": acc,
        "baseline": baseline,
        "gain": acc - baseline,
        "model": model_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": n_rows,
    }


def main() -> None:
    metrics: dict[str, dict] = {}
    for league, cache_path in LEAGUES.items():
        result = _train_one(league, cache_path)
        if result is not None:
            metrics[league] = result

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = MODELS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    logger.info("Métriques écrites dans %s", metrics_path)


if __name__ == "__main__":
    main()
