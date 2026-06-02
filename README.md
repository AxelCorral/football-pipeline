# football-pipeline

[![pipeline status](https://gitlab.com/NAMESPACE/football-pipeline/badges/main/pipeline.svg)](https://gitlab.com/NAMESPACE/football-pipeline/-/pipelines)
[![coverage](https://gitlab.com/NAMESPACE/football-pipeline/badges/main/coverage.svg)](https://gitlab.com/NAMESPACE/football-pipeline/-/pipelines)

> Remplacer `NAMESPACE` par votre namespace GitLab. L'URL exacte du badge
> est disponible dans **Settings → CI/CD → General pipelines → Pipeline status**.

Pipeline ETL Football — extraction de statistiques de matchs via **football-data.org**,
stockage sur **AWS S3** au format Parquet, transformation simulant **AWS Glue**,
requêtes via **AWS Athena**, et CI/CD **GitLab**.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           football-pipeline                              │
│                                                                          │
│  ┌──────────────────┐    ┌────────────────────┐    ┌─────────────────┐  │
│  │  football-       │    │   src/extract/     │    │    AWS S3       │  │
│  │  data.org API    │───▶│ football_api.py    │───▶│  raw/ Parquet   │  │
│  │  (REST v4)       │    │                    │    │                 │  │
│  └──────────────────┘    └────────────────────┘    └───────┬─────────┘  │
│                                                            │            │
│                                                   ┌────────▼─────────┐  │
│                                                   │  src/transform/  │  │
│                                                   │glue_transform.py │  │
│                                                   │  (Glue-like)     │  │
│                                                   └────────┬─────────┘  │
│                                                            │            │
│  ┌──────────────────┐    ┌────────────────────┐   ┌────────▼─────────┐  │
│  │   Dashboards /   │    │   AWS Athena       │   │    AWS S3        │  │
│  │   Analyses       │◀───│ src/query/         │◀──│ curated/ Parquet │  │
│  │                  │    │ athena_query.py    │   │                  │  │
│  └──────────────────┘    └────────────────────┘   └──────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        GitLab CI/CD                                │  │
│  │   lint:flake8 ──▶ lint:black ──▶ test:unit ──▶ deploy:pipeline    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Stack

| Composant        | Technologie                        |
|------------------|------------------------------------|
| Langage          | Python 3.12                        |
| AWS              | S3, Athena, Glue (simulé localement) |
| AWS SDK          | boto3                              |
| Data             | pandas, pyarrow (Parquet)          |
| Tests            | pytest                             |
| Linting          | flake8, black                      |
| CI/CD            | GitLab CI/CD                       |
| API source       | football-data.org v4               |

## Structure

```
football-pipeline/
├── .gitlab-ci.yml              # Pipeline CI/CD (lint → test → deploy)
├── pyproject.toml              # Config black & pytest
├── .flake8                     # Config flake8
├── requirements.txt            # Dépendances Python (pinned)
├── .env.example                # Variables d'environnement (modèle)
├── CLAUDE.md                   # Instructions pour Claude Code
├── src/
│   ├── main.py                 # Point d'entrée — orchestre le pipeline
│   ├── config/
│   │   └── settings.py         # Chargement .env & constantes
│   ├── extract/
│   │   └── football_api.py     # Client API football-data.org
│   ├── transform/
│   │   └── glue_transform.py   # Transformations pandas (Glue-like)
│   ├── load/
│   │   └── s3_loader.py        # Upload Parquet → S3 via boto3
│   └── query/
│       └── athena_query.py     # Exécution SQL sur Athena
└── tests/
    ├── conftest.py             # Fixtures partagées (Settings, données)
    ├── test_extract.py
    ├── test_transform.py
    ├── test_load.py
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
cp .env.example .env
# Renseigner les variables dans .env
```

## Utilisation

```bash
python src/main.py
```

## Tests

```bash
pytest tests/ -v
```

## Linting

```bash
flake8 src/ tests/
black src/ tests/
```

## Variables d'environnement

Voir `.env.example` pour le modèle complet.

| Variable                    | Description                            |
|-----------------------------|----------------------------------------|
| `FOOTBALL_API_KEY`          | Clé API football-data.org              |
| `AWS_ACCESS_KEY_ID`         | Credentials AWS                        |
| `AWS_SECRET_ACCESS_KEY`     | Credentials AWS                        |
| `AWS_REGION`                | Région AWS (défaut : `eu-west-1`)      |
| `S3_BUCKET_NAME`            | Bucket S3 cible                        |
| `S3_RAW_PREFIX`             | Préfixe zone brute (défaut : `raw/matches`) |
| `S3_CURATED_PREFIX`         | Préfixe zone curée (défaut : `curated/matches`) |
| `ATHENA_DATABASE`           | Base de données Athena                 |
| `ATHENA_TABLE_MATCHES`      | Table des matchs (défaut : `matches`)  |
| `ATHENA_OUTPUT_LOCATION`    | URI S3 pour les résultats Athena       |
