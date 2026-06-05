# Déploiement sur Streamlit Cloud

## Prérequis

1. **Générer le cache local** (nécessite des credentials AWS) :
   ```bash
   pip install -r requirements.txt
   python scripts/export_cache.py
   ```
   Cela crée `data/cache/matches_PL_2025.parquet`.

2. **Committer le cache** dans le repo (le fichier `.parquet` est inclus volontairement) :
   ```bash
   git add data/cache/matches_PL_2025.parquet
   git commit -m "data: add PL 2025 match cache for Streamlit app"
   git push
   ```

## Déploiement

### Option A — Streamlit Community Cloud (gratuit)

1. Aller sur [share.streamlit.io](https://share.streamlit.io)
2. Connecter votre compte GitHub (ou importer le repo depuis GitLab)
3. **New app** → sélectionner le repo et renseigner :
   - **Main file path** : `app.py`
   - **Python version** : 3.12
4. Dans **Advanced settings → Requirements file** : saisir `requirements_app.txt`
5. Cliquer **Deploy**

> L'app fonctionnera entièrement **sans credentials AWS** grâce au cache Parquet
> committé dans le repo.

### Variables d'environnement

**Aucune variable n'est nécessaire** pour le dashboard Streamlit.

Les credentials AWS ne sont requis que pour `scripts/export_cache.py`,
qui s'exécute en local avant le déploiement.

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
python scripts/export_cache.py
git add data/cache/matches_PL_2025.parquet
git commit -m "data: refresh PL cache $(date +%Y-%m-%d)"
git push
```

Streamlit Cloud redéploie automatiquement dès le push.

## Développement local

```bash
pip install -r requirements_app.txt
streamlit run app.py
```

L'app sera disponible sur `http://localhost:8501`.
