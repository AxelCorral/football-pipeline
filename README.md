# Football Pipeline — ETL + ML sur les 5 grands championnats européens

[![pipeline status](https://gitlab.com/axelcorral-group/football-pipeline/badges/main/pipeline.svg)](https://gitlab.com/axelcorral-group/football-pipeline/-/pipelines)
[![coverage](https://gitlab.com/axelcorral-group/football-pipeline/badges/main/coverage.svg)](https://gitlab.com/axelcorral-group/football-pipeline/-/pipelines)

Pipeline ETL complet qui collecte les données de matchs de **5 championnats européens** via l'API football-data.org, les stocke et transforme sur **AWS S3/Glue/Athena**, puis entraîne un modèle de **prédiction de résultat** (victoire domicile / nul / victoire extérieur) exposé dans un **dashboard Streamlit** déployable sans credentials AWS.

## Live Demo

> **[STREAMLIT_URL]** — remplacer après déploiement sur Streamlit Cloud

Le dashboard fonctionne entièrement hors-ligne grâce au cache Parquet versionné dans le repo (`data/cache/`).

## Architecture

```
football-data.org API (REST v4)
        │  GET /competitions/{code}/matches
        │  7 s de délai entre chaque compétition (rate limit free tier)
        ▼
src/ingestion/fetch_matches.py          ← fetch + retry + fallback 400
        │  JSON brut
        ▼
AWS S3  raw/{code}/{date}/matches.json
        │
        ▼
src/transform/process_matches.py        ← normalisation pandas (Glue-like)
        │  DataFrame normalisé (14 colonnes)
        ▼
AWS S3  curated/{code}/{season}/matches.parquet
        │                    │
        ▼                    ▼
AWS Athena              src/ml/features.py       ← rolling form 5 matchs
SQL analytique          src/ml/train.py          ← LR vs RandomForest
queries/*.sql           src/ml/evaluate.py       ← baseline naïve
                                │
                                ▼
                        data/cache/matches_all_2025.parquet
                                │
                                ▼
                        app.py (Streamlit)
                        Filtre par compétition · Classement · Prédiction
```

**Stages GitLab CI/CD :** `lint` → `test` → `model` → `build` → `deploy`

## Résultats ML — saison 2025/26

Modèle retenu : meilleur entre Logistic Regression et Random Forest, split temporel 80/20 (aucun shuffle).

| Championnat      | Code | Matchs | Accuracy | Baseline (toujours H) | Gain   |
|------------------|------|-------:|----------|-----------------------|--------|
| Premier League   | PL   |    380 | **43.1%** | 42.6%                | +0.5%  |
| Ligue 1          | FL1  |    306 | **47.4%** | 43.3%                | +4.1%  |
| Bundesliga       | BL1  |    306 | **43.1%** | 40.5%                | +2.6%  |
| Serie A          | SA   |    380 | **48.6%** | 44.5%                | +4.1%  |
| Primera Division | PD   |    380 | **49.3%** | 44.2%                | +5.1%  |

> La prédiction de résultats de football est un problème difficile. Ces chiffres sont cohérents avec la littérature (~50 % d'accuracy sur des features simples). L'intérêt du projet est le pipeline, pas la performance absolue du modèle.

## Données

| Paramètre | Valeur |
|-----------|--------|
| Source | football-data.org API v4 (free tier) |
| Compétitions | PL, FL1, BL1, SA, PD |
| Saison | 2025/26 |
| Total matchs | 1 752 (380+306+306+380+380) |
| Stockage brut | S3 `raw/` — JSON par compétition/date |
| Stockage curé | S3 `curated/` — Parquet partitionné par saison |
| Cache local | `data/cache/matches_all_2025.parquet` |

## Stack

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.12 |
| AWS | S3 · Athena · Glue (simulé pandas) |
| AWS SDK | boto3 |
| Data | pandas 2.3 · pyarrow 24 (Parquet) |
| ML | scikit-learn 1.7 · joblib 1.5 |
| Dashboard | Streamlit 1.58 · Plotly 6 |
| Tests | pytest · coverage ≥ 70 % |
| Linting | flake8 · black |
| CI/CD | GitLab CI/CD |
| API source | football-data.org v4 |

## Structure

```
football-pipeline/
├── app.py                          # Dashboard Streamlit (4 pages)
├── requirements.txt                # Dépendances pipeline (pinned)
├── requirements_app.txt            # Dépendances Streamlit uniquement
├── .gitlab-ci.yml                  # lint → test → model → build → deploy
├── pyproject.toml                  # Config black & pytest
├── README_DEPLOY.md                # Instructions déploiement Streamlit Cloud
│
├── src/
│   ├── config/                     # Chargement .env & dataclass Config
│   ├── ingestion/
│   │   └── fetch_matches.py        # Fetch API + retry + upload S3 JSON
│   ├── extract/
│   │   └── football_api.py         # Client API football-data.org (stub)
│   ├── transform/
│   │   ├── process_matches.py      # load_raw_from_s3 · transform · save_as_parquet
│   │   └── glue_transform.py       # GlueTransformer (pandas Glue-like)
│   ├── load/
│   │   └── s3_loader.py            # Upload Parquet → S3
│   ├── ml/
│   │   ├── features.py             # Rolling form 5 matchs (FEATURE_COLS)
│   │   ├── train.py                # LR vs RF · split temporel 80/20 · joblib
│   │   └── evaluate.py             # Baseline naïve (toujours H)
│   ├── query/
│   │   └── athena_query.py         # AthenaQueryRunner
│   ├── analytics/
│   │   └── athena_queries.py       # Requêtes analytiques métier
│   └── utils/
│       └── logger.py               # Logger structuré
│
├── scripts/
│   ├── ingest_all.py               # Ingestion 5 compétitions × N saisons
│   └── export_cache.py             # S3 → data/cache/ (Parquet local)
│
├── data/
│   └── cache/                      # Parquet commités (app offline)
│       ├── matches_all_2025.parquet
│       ├── matches_PL_2025.parquet
│       ├── matches_FL1_2025.parquet
│       ├── matches_BL1_2025.parquet
│       ├── matches_SA_2025.parquet
│       └── matches_PD_2025.parquet
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
    └── test_query.py
```

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # puis renseigner les variables
```

## Utilisation

### Ingestion complète (5 compétitions)

```bash
# Ingère via l'API et uploade sur S3 (nécessite credentials AWS + API_KEY)
python scripts/ingest_all.py --season 2025
```

### Export du cache local (pour l'app Streamlit)

```bash
# Lit S3, transforme, sauvegarde dans data/cache/
python scripts/export_cache.py --season 2025
```

### Dashboard Streamlit

```bash
pip install -r requirements_app.txt
streamlit run app.py
```

### Tests

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing   # avec coverage
```

### Linting

```bash
flake8 src/ tests/ --max-line-length 100
black src/ tests/
```

## Variables d'environnement

Voir `.env.example` pour le modèle complet.

| Variable | Description |
|----------|-------------|
| `API_KEY` | Clé API football-data.org |
| `FOOTBALL_API_BASE_URL` | Base URL API (défaut : `https://api.football-data.org/v4`) |
| `AWS_BUCKET_NAME` | Bucket S3 cible |
| `AWS_REGION` | Région AWS (défaut : `eu-west-1`) |
| `ATHENA_DATABASE` | Base de données Athena |
| `ATHENA_OUTPUT_S3` | URI S3 pour les résultats Athena |

> Les credentials AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) sont lus depuis `~/.aws/credentials` ou l'environnement — non stockés dans `.env`.

## Limitations connues

- **Une seule saison** : le free tier de football-data.org ne supporte pas le filtre `season` — les données couvrent uniquement la saison courante (2025/26).
- **Features simples** : rolling moyenne sur 5 matchs (buts, points) sans xG, sans classement FIFA/UEFA, sans données joueurs.
- **Pas de validation croisée temporelle** : un seul split 80/20, résultats à prendre avec prudence sur des sous-ensembles de données réduits (FL1/BL1 : 306 matchs).
- **Modèle non persisté en production** : l'entraînement se fait à chaque démarrage de l'app Streamlit (quelques secondes, mis en cache par `st.cache_resource`).
- **Données football-data.org** : certains champs (venue, referee) sont absents pour une partie des matchs selon la compétition.
