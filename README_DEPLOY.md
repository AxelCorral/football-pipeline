# Déploiement sur Streamlit Cloud

## Prérequis

Le dashboard ne lit que les marts dbt exportés en Parquet. Les produire demande
trois étapes, dont une seule a besoin d'AWS.

1. **Rafraîchir l'instantané de la zone curated** (credentials AWS requis) :
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   python scripts/export_cache.py
   ```
   Cela écrit `data/cache/matches_{CODE}_2025.parquet` et
   `data/cache/matches_all_2025.parquet`.

2. **Construire et tester la couche dbt**, puis exporter les marts (aucun
   credential : la cible `dev` lit l'instantané ci-dessus) :
   ```bash
   pip install -r requirements-dbt.txt        # dans .venv-dbt, voir README
   export DBT_PROFILES_DIR=$PWD/dbt
   dbt deps  --project-dir dbt
   dbt build --project-dir dbt --target dev
   python scripts/export_marts.py --source duckdb
   ```

   Ou, si le compte dispose des droits Athena, directement depuis la
   production : `dbt build --project-dir dbt --target athena` puis
   `python scripts/export_marts.py`.

3. **Committer les marts** (les `.parquet` de `data/marts/` sont versionnés
   volontairement) :
   ```bash
   git add data/cache/*.parquet data/marts/*.parquet
   git commit -m "data: refresh dbt marts"
   git push
   ```

## Déploiement

### Option A — Streamlit Community Cloud (gratuit)

1. Aller sur [share.streamlit.io](https://share.streamlit.io)
2. Connecter votre compte GitHub (ou importer le repo depuis GitLab)
3. **New app** → sélectionner le repo et renseigner :
   - **Main file path** : `app.py`
   - **Python version** : 3.12
4. Cliquer **Deploy**

> Streamlit Cloud installe automatiquement le `requirements.txt` **à la racine**
> du repo ; il n'existe pas de réglage pour pointer vers un autre fichier.
> C'est pourquoi `requirements.txt` contient aussi `streamlit` et `plotly`.

> L'app fonctionnera entièrement **sans credentials AWS** grâce aux marts
> Parquet committés dans `data/marts/`.

### Variables d'environnement

**Aucune variable n'est nécessaire** pour le dashboard Streamlit.

Les credentials AWS ne sont requis que pour `scripts/export_cache.py` (ou pour
un `dbt build --target athena`), qui s'exécutent en local avant le déploiement.

### Option B — Docker (auto-hébergé)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements_app.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

```bash
docker build -t football-pipeline .
docker run -p 8501:8501 football-pipeline
```

## Mise à jour des données

Pour rafraîchir le cache avec les derniers matchs :

```bash
python scripts/export_cache.py                    # S3 -> data/cache/
dbt build --project-dir dbt --target dev          # modèles + tests
python scripts/export_marts.py --source duckdb    # -> data/marts/
python scripts/train_all_models.py                # modèles + metrics.json
git add data/cache/*.parquet data/marts/*.parquet models/
git commit -m "data: refresh marts $(date +%Y-%m-%d)"
git push
```

Streamlit Cloud redéploie automatiquement dès le push.

## Développement local

```bash
pip install -r requirements_app.txt
streamlit run app.py
```

L'app sera disponible sur `http://localhost:8501`.
