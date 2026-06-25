# Football Pipeline — ETL + ML sur les 5 grands championnats européens

🇫🇷 Français | 🇬🇧 [English](README.md)

[![pipeline status](https://gitlab.com/axelcorral-group/football-pipeline/badges/main/pipeline.svg)](https://gitlab.com/axelcorral-group/football-pipeline/-/pipelines)
[![coverage](https://gitlab.com/axelcorral-group/football-pipeline/badges/main/coverage.svg)](https://gitlab.com/axelcorral-group/football-pipeline/-/pipelines)

Pipeline ETL complet qui collecte les données de matchs de **5 championnats européens** via l'API football-data.org, les stocke et transforme sur **AWS S3 / Athena**, puis entraîne un modèle de **prédiction de résultat** (victoire domicile / nul / victoire extérieur) exposé dans un **dashboard Streamlit** déployable sans credentials AWS.

> Ce projet n'a pas pour but de prédire le football avec précision — le modèle est volontairement simple et son accuracy (43–49 %) reste proche d'une baseline naïve. Son objectif est de démontrer l'**industrialisation d'un pipeline data de bout en bout** avec les pratiques d'ingénierie attendues en production.

## Live Demo

**https://football-pipeline-axel.streamlit.app**

Le dashboard fonctionne entièrement hors-ligne grâce au cache Parquet versionné dans le repo (`data/cache/`) et aux modèles pré-entraînés versionnés (`models/`).

## Architecture

```
football-data.org API (REST v4)
        │  GET /competitions/{code}/matches
        │  7 s de délai entre chaque compétition (rate limit free tier)
        ▼
src/ingestion/fetch_matches.py          ← fetch + retry + fallback 400
        │  JSON brut
        ▼
AWS S3  raw/{code}/{date}/matches.json          ← zone brute immuable
        │
        ▼
src/transform/process_matches.py        ← normalisation pandas (Glue-like)
        │  DataFrame normalisé (14 colonnes)
        ▼
AWS S3  curated/{code}/{season}/matches.parquet ← zone curée
        │                    │
        ▼                    ▼
AWS Athena              src/ml/features.py       ← rolling form 5 matchs (shift(1))
SQL analytique          src/ml/train.py          ← LR vs RandomForest
queries/*.sql           scripts/train_all_models.py ← 1 modèle / ligue + global
                                │
                                ▼
                        models/match_predictor_{league}.joblib + metrics.json
                                │
                                ▼
                        src/ml/inference.py      ← chargement modèle (serving)
                                │
                                ▼
                        app.py (Streamlit)
                        Filtre par compétition · Classement · Prédiction
```

**Orchestrateur :** `python -m src.main` (avec `--competition`, `--season`, `--dry-run`)
**Stages GitLab CI/CD :** `lint` → `test` → `model` → `build` → `deploy`

## Résultats ML — saison 2025/26

Modèle retenu : meilleur entre Logistic Regression et Random Forest, split **temporel 80/20 (aucun shuffle)**. Chiffres issus de `models/metrics.json`.

| Championnat       | Code | Modèle              | Accuracy | Baseline (toujours H) | Gain      | n (entraînement) |
|-------------------|------|---------------------|---------:|----------------------:|----------:|-----------------:|
| Premier League    | PL   | Logistic Regression | 43.1 %   | 42.6 %                | +0.4 pt   | 360              |
| Ligue 1           | FL1  | Logistic Regression | 47.4 %   | 46.2 %                | +1.1 pt   | 285              |
| Bundesliga        | BL1  | Logistic Regression | 43.1 %   | 43.8 %                | −0.7 pt   | 288              |
| Serie A           | SA   | Logistic Regression | 48.6 %   | 38.9 %                | +9.7 pt   | 356              |
| La Liga           | PD   | Logistic Regression | 49.3 %   | 48.9 %                | +0.3 pt   | 355              |
| Toutes ligues     | all  | Random Forest       | 44.7 %   | 44.0 %                | +0.6 pt   | 1644             |

> La prédiction de résultats de football est un problème difficile. Seule la Serie A montre un gain net ; sur les autres ligues le modèle apporte un gain marginal voire négatif (Bundesliga). L'intérêt du projet est le pipeline et le cycle de vie ML, pas la performance absolue du modèle. Voir [`models/model_card.md`](models/model_card.md) pour le détail des features, performances et limites.

## Données

| Paramètre | Valeur |
|-----------|--------|
| Source | football-data.org API v4 (free tier) |
| Compétitions | PL, FL1, BL1, SA, PD |
| Saison | 2025/26 |
| Volume | ~1 750 matchs bruts collectés, 1 644 lignes exploitables après features |
| Stockage brut | S3 `raw/` — JSON par compétition/date (immuable) |
| Stockage curé | S3 `curated/` — Parquet partitionné par saison |
| Cache local | `data/cache/matches_all_2025.parquet` |

## Stack

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.12 |
| AWS | S3 · Athena · Glue (simulé pandas) |
| AWS SDK | boto3 |
| Data | pandas · pyarrow (Parquet) |
| ML | scikit-learn · joblib |
| Dashboard | Streamlit · Plotly |
| Tests | pytest · coverage ≥ 70 % |
| Linting | flake8 · black |
| CI/CD | GitLab CI/CD |
| API source | football-data.org v4 |

## Ce que ce projet démontre pour un poste de Data Engineer

Ce projet ne vise pas à prédire le football avec précision — le modèle est
volontairement simple et son accuracy (43–49 %) reste proche d'une baseline
naïve. Ce qu'il démontre, c'est la capacité à **industrialiser un pipeline
data complet de bout en bout**, avec les pratiques attendues en production :

- **Ingestion** depuis une API REST externe (football-data.org) avec retry,
  backoff et gestion du rate-limit.
- **Stockage cloud structuré** sur AWS S3 selon un pattern data lake raw / curated.
- **Transformation** du JSON brut vers du Parquet partitionné.
- **Requêtage analytique** via AWS Athena (SQL serverless sur fichiers S3).
- **Un cycle de vie ML propre** : entraînement séparé du serving, artefacts de
  modèle versionnés, métriques tracées, model card documentée.
- **CI/CD automatisé** sur GitLab : linting, tests, gate de coverage, build, deploy.
- **Un dashboard déployé et reproductible** que n'importe qui peut ouvrir et lancer.

Le sujet, c'est l'infrastructure autour du modèle — collecter, stocker
proprement, transformer, tester et déployer de façon fiable — pas la
performance prédictive. Cette distinction (Data Engineering vs Data Science)
est intentionnelle.

## Décisions d'architecture

Quelques choix de conception qui méritent une explication, car chacun est un
arbitrage assumé :

**Séparation raw / curated sur S3.** La zone `raw/` contient la donnée exactement
telle que l'API l'a renvoyée (JSON intact) et est traitée comme immuable. La zone
`curated/` contient le Parquet nettoyé et transformé que consomment le modèle et
le dashboard. Si un bug est découvert dans la transformation, le pipeline peut
être rejoué depuis la donnée `raw/` intacte sans jamais re-solliciter l'API.
Séparer la donnée source immuable de la donnée travaillée est le fondement d'un
data lake.

**S3 + Athena plutôt qu'une base managée.** La donnée est collectée en batch et
interrogée ponctuellement pour de l'analytique — elle ne change pas en continu.
Une base de données tournant en permanence (ex. PostgreSQL) impliquerait de payer
du compute inactif. Avec S3 + Athena, le stockage coûte quelques centimes et les
requêtes ne sont facturées que lorsqu'elles sont exécutées (analytique
serverless). Le bon outil pour des charges analytiques batch sur données peu
changeantes.

**Modèles pré-entraînés versionnés, pas ré-entraînés au démarrage.** Le dashboard
charge des artefacts `.joblib` pré-entraînés au lieu de ré-entraîner le modèle à
chaque visite. Cela rend le chargement de page rapide, ne sollicite les données
d'entraînement qu'une seule fois (au build) au lieu de chaque visite utilisateur,
et sépare proprement la phase d'entraînement de la phase de serving — la structure
standard de tout système ML en production.

**Un modèle par ligue plutôt qu'un modèle global unique.** Chaque championnat a
ses propres caractéristiques et dynamiques, qui produisent des patterns prédictifs
réellement différents (la Serie A gagne +9.7 points sur la baseline, la Bundesliga
est légèrement négative). Un modèle par ligue préserve cette granularité ; un
modèle global unique diluerait le signal spécifique à chaque championnat. Un
modèle global `all` est également entraîné et conservé, pour la vue combinée.

## Cycle de vie du modèle & reproductibilité

Le workflow ML est conçu pour être traçable et reproductible, pas une boîte noire :

- **L'entraînement est une étape dédiée et explicite** (`scripts/train_all_models.py`),
  jamais déclenchée implicitement par le dashboard.
- **Split temporel 80/20, sans shuffle.** Comme les matchs sont ordonnés dans le
  temps, les 80 % les plus anciens servent à l'entraînement et les 20 % les plus
  récents au test. Un shuffle aléatoire laisserait le modèle « voir » des matchs
  futurs pendant l'entraînement et fuiter silencieusement de l'information —
  gonflant une accuracy qui s'effondrerait en pratique. Le split temporel l'empêche.
- **Features anti-leakage.** Chaque statistique de forme glissante est calculée
  avec `shift(1)`, de sorte qu'un match n'est jamais inclus dans le calcul de ses
  propres features. Sans cela, le modèle utiliserait le résultat même qu'il est
  censé prédire — une fuite subtile et invisible.
- **Métriques tracées.** Chaque entraînement écrit `models/metrics.json` (accuracy,
  baseline, gain, modèle retenu, date d'entraînement, nombre de lignes par ligue),
  pour qu'on sache toujours quel modèle tourne et comment il a performé.
- **Une model card** (`models/model_card.md`) documente l'usage prévu, les features,
  les performances par ligue et — surtout — les limites connues du modèle, honnêtement.

Reproduire l'ensemble des modèles :

```bash
python scripts/train_all_models.py
```

## Structure

```
football-pipeline/
├── app.py                          # Dashboard Streamlit (4 pages)
├── requirements.txt                # Dépendances pipeline core (pinned)
├── requirements-dev.txt            # Dépendances dev/test/CI
├── requirements_app.txt            # Dépendances Streamlit uniquement
├── .gitlab-ci.yml                  # lint → test → model → build → deploy
├── pyproject.toml                  # Config black & pytest
├── README_DEPLOY.md                # Instructions déploiement Streamlit Cloud
│
├── src/
│   ├── main.py                     # Orchestrateur ETL (CLI + --dry-run)
│   ├── config/                     # Chargement .env & dataclass Config
│   ├── ingestion/
│   │   └── fetch_matches.py        # Fetch API + retry + upload S3 JSON
│   ├── transform/
│   │   ├── process_matches.py      # load_raw_from_s3 · transform · save_as_parquet
│   │   └── glue_transform.py       # GlueTransformer (pandas Glue-like)
│   ├── load/
│   │   └── s3_loader.py            # Upload Parquet → S3
│   ├── ml/
│   │   ├── features.py             # Rolling form 5 matchs (shift(1) anti-leakage)
│   │   ├── train.py                # LR vs RF · split temporel 80/20 · joblib
│   │   ├── inference.py            # Chargement modèle pré-entraîné (serving)
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
│   ├── train_all_models.py         # Entraîne 5 modèles / ligue + global + metrics.json
│   └── export_cache.py             # S3 → data/cache/ (Parquet local)
│
├── models/
│   ├── match_predictor_{PL,FL1,BL1,SA,PD,all}.joblib   # Modèles versionnés
│   ├── metrics.json                # Accuracy/baseline/gain/date/n par ligue
│   └── model_card.md               # Fiche modèle (usage, features, limites)
│
├── data/
│   └── cache/                      # Parquet commités (app offline)
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
    ├── test_main.py                # orchestrateur (dry-run, CLI, erreurs)
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
cp .env.example .env   # puis renseigner les variables
```

## Utilisation

### Pipeline complet (orchestrateur)

```bash
python -m src.main                         # 5 compétitions
python -m src.main --competition PL        # une seule compétition
python -m src.main --dry-run               # simulation, sans appel API/S3
```

### Entraînement des modèles

```bash
python scripts/train_all_models.py         # 5 modèles/ligue + global + metrics.json
```

### Dashboard Streamlit

```bash
pip install -r requirements_app.txt
streamlit run app.py
```

### Tests & Linting

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing   # avec coverage
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
- **Petits échantillons par ligue** : 285 à 360 lignes d'entraînement selon la compétition — le jeu de test (~57 à ~72 matchs) rend les écarts d'accuracy peu significatifs statistiquement.
- **Pas de validation croisée temporelle** : un seul split 80/20, sans estimation de la variance de performance (walk-forward / expanding window).
- **Gain négatif sur la Bundesliga** : le modèle y fait moins bien que la baseline naïve « toujours victoire à domicile ».
- **Données football-data.org** : certains champs (venue, referee) sont absents pour une partie des matchs selon la compétition.
