# Football Pipeline — ETL + ML on the Big 5 European Leagues

🇬🇧 English | 🇫🇷 [Français](README.fr.md)

[![pipeline status](https://gitlab.com/axelcorral-group/football-pipeline/badges/main/pipeline.svg)](https://gitlab.com/axelcorral-group/football-pipeline/-/pipelines)
[![coverage](https://gitlab.com/axelcorral-group/football-pipeline/badges/main/coverage.svg)](https://gitlab.com/axelcorral-group/football-pipeline/-/pipelines)

A complete ETL pipeline that collects match data from the **Big 5 European leagues** via the football-data.org API, stores and transforms it on **AWS S3 / Athena**, then trains a **match outcome prediction** model (home win / draw / away win) served through a **Streamlit dashboard** deployable without AWS credentials.

> This project is not about predicting football accurately — the model is deliberately simple and its accuracy (43–49%) sits close to a naive baseline. Its purpose is to demonstrate the **end-to-end industrialization of a data pipeline** with the engineering practices expected in production.

## Live Demo

**https://football-pipeline-axel.streamlit.app**

The dashboard runs fully offline thanks to the Parquet cache versioned in the repo (`data/cache/`) and the pre-trained models versioned in `models/`.

## Architecture

```
football-data.org API (REST v4)
        │  GET /competitions/{code}/matches
        │  7s delay between competitions (free-tier rate limit)
        ▼
src/ingestion/fetch_matches.py          ← fetch + retry + 400 fallback
        │  raw JSON
        ▼
AWS S3  raw/{code}/{date}/matches.json          ← immutable raw zone
        │
        ▼
src/transform/process_matches.py        ← pandas normalization (Glue-like)
        │  normalized DataFrame (14 columns)
        ▼
AWS S3  curated/{code}/{season}/matches.parquet ← curated zone
        │                    │
        ▼                    ▼
AWS Athena              src/ml/features.py       ← rolling form 5 matches (shift(1))
analytical SQL          src/ml/train.py          ← LR vs RandomForest
queries/*.sql           scripts/train_all_models.py ← 1 model / league + global
                                │
                                ▼
                        models/match_predictor_{league}.joblib + metrics.json
                                │
                                ▼
                        src/ml/inference.py      ← model loading (serving)
                                │
                                ▼
                        app.py (Streamlit)
                        Competition filter · Standings · Prediction
```

**Orchestrator:** `python -m src.main` (with `--competition`, `--season`, `--dry-run`)
**GitLab CI/CD stages:** `lint` → `test` → `model` → `build` → `deploy`

## ML Results — 2025/26 season

Retained model: best of Logistic Regression and Random Forest, **temporal 80/20 split (no shuffle)**. Figures from `models/metrics.json`.

| League            | Code | Model               | Accuracy | Baseline (always H) | Gain      | n (training) |
|-------------------|------|---------------------|---------:|--------------------:|----------:|-------------:|
| Premier League    | PL   | Logistic Regression | 43.1%    | 42.6%               | +0.4 pt   | 360          |
| Ligue 1           | FL1  | Logistic Regression | 47.4%    | 46.2%               | +1.1 pt   | 285          |
| Bundesliga        | BL1  | Logistic Regression | 43.1%    | 43.8%               | −0.7 pt   | 288          |
| Serie A           | SA   | Logistic Regression | 48.6%    | 38.9%               | +9.7 pt   | 356          |
| La Liga           | PD   | Logistic Regression | 49.3%    | 48.9%               | +0.3 pt   | 355          |
| All leagues       | all  | Random Forest       | 44.7%    | 44.0%               | +0.6 pt   | 1644         |

> Football outcome prediction is a hard problem. Only Serie A shows a clear gain; on the other leagues the model adds marginal or even negative value (Bundesliga). The value of this project is the pipeline and the ML lifecycle, not the model's raw performance. See [`models/model_card.md`](models/model_card.md) for full features, performance and limitations.

## Data

| Parameter | Value |
|-----------|-------|
| Source | football-data.org API v4 (free tier) |
| Competitions | PL, FL1, BL1, SA, PD |
| Season | 2025/26 |
| Volume | ~1,750 raw matches collected, 1,644 usable rows after feature computation |
| Raw storage | S3 `raw/` — JSON per competition/date (immutable) |
| Curated storage | S3 `curated/` — Parquet partitioned by season |
| Local cache | `data/cache/matches_all_2025.parquet` |

## Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| AWS | S3 · Athena · Glue (pandas-simulated) |
| AWS SDK | boto3 |
| Data | pandas · pyarrow (Parquet) |
| ML | scikit-learn · joblib |
| Dashboard | Streamlit · Plotly |
| Tests | pytest · coverage ≥ 70% |
| Linting | flake8 · black |
| CI/CD | GitLab CI/CD |
| API source | football-data.org v4 |

## What This Project Demonstrates for a Data Engineer Role

This project is not about predicting football accurately — the model is
deliberately simple and its accuracy (43–49%) sits close to a naive baseline.
What it demonstrates is the ability to **industrialize a complete data pipeline
end to end**, with the engineering practices expected in production:

- **Ingestion** from an external REST API (football-data.org) with retry,
  backoff and rate-limit handling.
- **Structured cloud storage** on AWS S3 following a raw / curated lake pattern.
- **Transformation** from raw JSON to partitioned Parquet.
- **Analytical querying** via AWS Athena (serverless SQL over S3 files).
- **A clean ML lifecycle**: training separated from serving, versioned model
  artifacts, tracked metrics, documented model card.
- **Automated CI/CD** on GitLab: linting, tests, coverage gate, build, deploy.
- **A deployed, reproducible dashboard** anyone can open and run.

The point is the infrastructure around the model — collecting, storing,
transforming, testing and deploying reliably — not the model's predictive
power. That distinction (Data Engineering vs Data Science) is intentional.

## Architecture Decisions

A few design choices worth explaining, because each was a deliberate tradeoff:

**Raw / curated separation on S3.** The `raw/` zone holds the data exactly as
the API returned it (untouched JSON) and is treated as immutable. The `curated/`
zone holds the cleaned, transformed Parquet that the model and dashboard consume.
If a bug is found in the transformation logic, the pipeline can be replayed from
the intact `raw/` data without ever re-hitting the API. Separating immutable
source data from processed data is the foundation of a data lake.

**S3 + Athena instead of a managed database.** The data is collected in batch and
queried occasionally for analytics — it does not change continuously. A
permanently running database (e.g. PostgreSQL) would mean paying for idle compute.
With S3 + Athena, storage costs cents and queries are billed only when run
(serverless analytics). The right tool for batch analytical workloads on
slowly-changing data.

**Pre-trained models committed to the repo, not retrained on startup.** The
dashboard loads pre-trained `.joblib` artifacts instead of retraining the model on
each visit. This makes page loads fast, calls the training data only once (at
build time) instead of on every user visit, and cleanly separates the training
phase from the serving phase — the standard structure of any production ML system.

**One model per league rather than a single global model.** Each championship has
its own characteristics and dynamics, which produce genuinely different predictive
patterns (Serie A gains +9.7 points over baseline, Bundesliga is slightly
negative). A per-league model preserves this granularity; a single global model
would dilute league-specific signal. A global `all` model is also trained and
kept, for the combined view.

## Model Lifecycle & Reproducibility

The ML workflow is built to be traceable and reproducible, not a black box:

- **Training is a dedicated, explicit step** (`scripts/train_all_models.py`),
  never triggered implicitly by the dashboard.
- **Temporal 80/20 split, no shuffle.** Because matches are time-ordered, the
  oldest 80% are used for training and the most recent 20% for testing. A random
  shuffle would let the model "see" future matches during training and silently
  leak information — inflating accuracy that would collapse in practice. The
  temporal split prevents this.
- **Anti-leakage features.** Each rolling form statistic is computed with
  `shift(1)` so a match is never included in the computation of its own features.
  Without this, the model would use the very result it is meant to predict — a
  subtle, invisible leak.
- **Tracked metrics.** Every training run writes `models/metrics.json` (accuracy,
  baseline, gain, retained model, training date, row count per league), so it is
  always clear which model is running and how it performed.
- **A model card** (`models/model_card.md`) documents intended use, features,
  per-league performance and — importantly — the model's known limitations
  honestly.

Reproduce the full model set with:

```bash
python scripts/train_all_models.py
```

## Project Structure

```
football-pipeline/
├── app.py                          # Streamlit dashboard (4 pages)
├── requirements.txt                # Core pipeline dependencies (pinned)
├── requirements-dev.txt            # Dev/test/CI dependencies
├── requirements_app.txt            # Streamlit-only dependencies
├── .gitlab-ci.yml                  # lint → test → model → build → deploy
├── pyproject.toml                  # black & pytest config
├── README_DEPLOY.md                # Streamlit Cloud deployment notes
│
├── src/
│   ├── main.py                     # ETL orchestrator (CLI + --dry-run)
│   ├── config/                     # .env loading & Config dataclass
│   ├── ingestion/
│   │   └── fetch_matches.py        # API fetch + retry + S3 JSON upload
│   ├── transform/
│   │   ├── process_matches.py      # load_raw_from_s3 · transform · save_as_parquet
│   │   └── glue_transform.py       # GlueTransformer (pandas Glue-like)
│   ├── load/
│   │   └── s3_loader.py            # Upload Parquet → S3
│   ├── ml/
│   │   ├── features.py             # Rolling form 5 matches (shift(1) anti-leakage)
│   │   ├── train.py                # LR vs RF · temporal 80/20 split · joblib
│   │   ├── inference.py            # Pre-trained model loading (serving)
│   │   └── evaluate.py             # Naive baseline (always H)
│   ├── query/
│   │   └── athena_query.py         # AthenaQueryRunner
│   ├── analytics/
│   │   └── athena_queries.py       # Business analytical queries
│   └── utils/
│       └── logger.py               # Structured logger
│
├── scripts/
│   ├── ingest_all.py               # Ingest 5 competitions × N seasons
│   ├── train_all_models.py         # Train 5 per-league models + global + metrics.json
│   └── export_cache.py             # S3 → data/cache/ (local Parquet)
│
├── models/
│   ├── match_predictor_{PL,FL1,BL1,SA,PD,all}.joblib   # Versioned models
│   ├── metrics.json                # Accuracy/baseline/gain/date/n per league
│   └── model_card.md               # Model card (use, features, limitations)
│
├── data/
│   └── cache/                      # Committed Parquet (offline app)
│       ├── matches_all_2025.parquet
│       └── matches_{PL,FL1,BL1,SA,PD}_2025.parquet
│
├── queries/
│   ├── avg_goals_per_round.sql
│   ├── home_advantage.sql
│   └── top_scorers.sql
│
└── tests/
    ├── conftest.py
    ├── test_extract.py
    ├── test_ingestion.py           # fetch_matches + fetch_all_competitions
    ├── test_transform.py
    ├── test_load.py
    ├── test_ml.py                  # features · train · evaluate
    ├── test_main.py                # orchestrator (dry-run, CLI, error handling)
    └── test_query.py
```

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # then fill in the variables
```

## Usage

### Full pipeline (orchestrator)

```bash
python -m src.main                         # 5 competitions
python -m src.main --competition PL        # single competition
python -m src.main --dry-run               # simulation, no API/S3 call
```

### Model training

```bash
python scripts/train_all_models.py         # 5 per-league models + global + metrics.json
```

### Streamlit dashboard

```bash
pip install -r requirements_app.txt
streamlit run app.py
```

### Tests & Linting

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing   # with coverage
flake8 src/ tests/ --max-line-length 100
black src/ tests/
```

## Environment Variables

See `.env.example` for the full template.

| Variable | Description |
|----------|-------------|
| `API_KEY` | football-data.org API key |
| `FOOTBALL_API_BASE_URL` | API base URL (default: `https://api.football-data.org/v4`) |
| `AWS_BUCKET_NAME` | Target S3 bucket |
| `AWS_REGION` | AWS region (default: `eu-west-1`) |
| `ATHENA_DATABASE` | Athena database |
| `ATHENA_OUTPUT_S3` | S3 URI for Athena results |

> AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) are read from `~/.aws/credentials` or the environment — never stored in `.env`.

## Known Limitations

- **Single season**: football-data.org's free tier does not support the `season` filter — the data only covers the current season (2025/26).
- **Simple features**: rolling 5-match average (goals, points) without xG, FIFA/UEFA ranking, or player-level data.
- **Small per-league samples**: 285 to 360 training rows per competition — the test set (~57 to ~72 matches) makes accuracy differences statistically weak.
- **No temporal cross-validation**: a single 80/20 split, with no variance estimate (walk-forward / expanding window).
- **Negative gain on Bundesliga**: the model performs worse there than the naive "always home win" baseline.
- **football-data.org data**: some fields (venue, referee) are missing for part of the matches depending on the competition.
