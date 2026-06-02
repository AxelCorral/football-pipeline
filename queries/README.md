# Requêtes analytiques — football-pipeline

Requêtes SQL exécutées sur **AWS Athena** contre la table `matches` pointant
vers les fichiers Parquet du préfixe `curated/` sur S3.

---

## Prérequis

### Table Athena

La table `matches` est définie par le catalogue AWS Glue, qui crawle le préfixe
`curated/{competition_code}/{season}/` du bucket S3. Schéma attendu :

| Colonne           | Type Athena  | Description                                    |
|-------------------|--------------|------------------------------------------------|
| `match_id`        | `BIGINT`     | Identifiant unique du match (API football-data)|
| `date`            | `TIMESTAMP`  | Date et heure UTC du match                     |
| `competition`     | `VARCHAR`    | Nom de la compétition (ex : "Premier League")  |
| `competition_code`| `VARCHAR`    | Code court (ex : "PL", "BL1", "SA")            |
| `season`          | `BIGINT`     | Année de début de saison (ex : 2023 → 2023/24) |
| `home_team`       | `VARCHAR`    | Équipe à domicile                              |
| `away_team`       | `VARCHAR`    | Équipe à l'extérieur                           |
| `home_goals`      | `BIGINT`     | Buts à domicile (NULL si match non joué)       |
| `away_goals`      | `BIGINT`     | Buts à l'extérieur (NULL si match non joué)    |
| `total_goals`     | `BIGINT`     | Somme home + away (NULL si match non joué)     |
| `result`          | `VARCHAR`    | `H` / `A` / `D` (NULL si non terminé)         |
| `status`          | `VARCHAR`    | `FINISHED` / `SCHEDULED` / `POSTPONED` …      |
| `referee`         | `VARCHAR`    | Nom de l'arbitre principal (peut être NULL)    |
| `venue`           | `VARCHAR`    | Stade (peut être NULL)                         |

> **Note `matchday`** : la colonne journée n'est pas encore dans le schéma
> curated. Pour une précision exacte dans `avg_goals_per_round.sql`, ajouter
> `matchday` dans `src/transform/process_matches.py` (champ disponible dans
> la réponse API `match["matchday"]`).

### Variables d'environnement

```
ATHENA_DATABASE=football_db
ATHENA_OUTPUT_S3=s3://football-pipeline-bucket/athena-results/
AWS_REGION=eu-west-1
```

---

## Lancer une requête depuis Python

```python
from src.analytics.athena_queries import run_athena_query, results_to_dataframe
from src.config import Config

config = Config.load()
sql = open("queries/top_scorers.sql").read()

qeid = run_athena_query(sql, config.athena_database, config.athena_output_s3)
df   = results_to_dataframe(qeid)
print(df)
```

---

## Requêtes disponibles

### `top_scorers.sql` — Top 10 équipes par buts marqués

**Objectif** : classer les équipes selon leur total de buts (domicile +
extérieur) sur toutes les saisons.

**Technique** : `UNION ALL` des buts domicile et extérieur → agrégation sur
l'équipe.

**Colonnes retournées** :

| Colonne             | Description                          |
|---------------------|--------------------------------------|
| `team`              | Nom de l'équipe                      |
| `total_goals_scored`| Buts marqués (domicile + extérieur)  |
| `matches_played`    | Nombre de matchs terminés            |
| `goals_per_game`    | Moyenne de buts par match            |

**Exemple de résultat** :

```
team                  total_goals_scored  matches_played  goals_per_game
Manchester City FC    312                 152             2.05
Bayern München        298                 136             2.19
…
```

---

### `home_advantage.sql` — Avantage du terrain par compétition

**Objectif** : mesurer l'avantage à domicile dans chaque compétition en
calculant les pourcentages de victoires domicile / extérieur / nul.

**Technique** : `CASE WHEN result = 'H'` + `NULLIF` pour éviter la division
par zéro.

**Colonnes retournées** :

| Colonne        | Description                                  |
|----------------|----------------------------------------------|
| `competition`  | Nom de la compétition                        |
| `total_matches`| Matchs terminés dans la compétition          |
| `home_wins`    | Victoires à domicile                         |
| `away_wins`    | Victoires à l'extérieur                      |
| `draws`        | Matchs nuls                                  |
| `home_win_pct` | % victoires domicile (arrondi 1 décimale)    |
| `away_win_pct` | % victoires extérieur (arrondi 1 décimale)   |
| `draw_pct`     | % nuls (arrondi 1 décimale)                  |

**Lecture** : `home_win_pct` > 40 % indique un fort avantage à domicile ;
la somme `home_win_pct + away_win_pct + draw_pct` doit être ≈ 100 %.

---

### `avg_goals_per_round.sql` — Moyenne de buts par journée

**Objectif** : identifier les journées prolifiques et suivre l'évolution du
rythme offensif saison par saison.

**Technique** : `DATE_TRUNC('week', "date")` regroupe les matchs d'une même
journée (généralement disputés sur 2-3 jours consécutifs).

**Colonnes retournées** :

| Colonne              | Description                                       |
|----------------------|---------------------------------------------------|
| `competition`        | Nom de la compétition                             |
| `season`             | Saison (année de début)                           |
| `round_week`         | Début de la semaine calendaire (proxy journée)    |
| `matches_in_round`   | Nombre de matchs joués cette semaine              |
| `goals_in_round`     | Total de buts de la journée                       |
| `avg_goals_per_match`| Moyenne de buts par match (arrondi 2 décimales)   |
| `max_goals_in_match` | Match le plus prolifique de la journée            |
| `min_goals_in_match` | Match le moins prolifique de la journée           |

**Cas d'usage** : comparer la moyenne de buts en début vs fin de saison,
ou repérer les journées sans matchs (trêve internationale).
