# La couche dbt

Ce document décrit la couche de transformation du projet : ce qu'elle
contient, pourquoi elle est en SQL plutôt qu'en Python, et comment elle
garantit qu'aucune feature ne connaît l'avenir.

Pour la référence colonne par colonne, `dbt docs generate --project-dir dbt`
puis `dbt docs serve --project-dir dbt` : chaque modèle et chaque colonne
importante y sont décrits, avec le DAG.

---

## Pourquoi dbt

Avant, une même idée — « la forme d'une équipe sur ses cinq derniers matchs » —
vivait à trois endroits : `src/ml/features.py` pour l'entraînement, une
reconstruction ad hoc dans `app.py` pour la page Prediction, et trois requêtes
SQL dans `queries/` pour l'analytique. Trois implémentations, trois occasions
de diverger, aucun test capable de le détecter.

dbt met cette logique à un seul endroit, en SQL, là où les données sont déjà :
dans Athena, au-dessus de la zone curated S3. Python garde ce qu'il fait mieux
— appels API, ingestion, écriture S3, apprentissage, inférence — et arrête de
refaire des jointures et des fenêtres glissantes que le moteur SQL exécute
mieux, et que dbt sait tester et documenter.

Le partage des responsabilités, concrètement :

| | Python | dbt |
|---|---|---|
| Appels API, retry, rate limit | ✔ | |
| Écriture raw JSON et curated Parquet sur S3 | ✔ | |
| Typage, nettoyage, déduplication | | ✔ |
| Règles métier H/D/A, points | | ✔ |
| Historique par équipe, fenêtres glissantes | | ✔ |
| Dataset de features, datasets analytics | | ✔ |
| Qualité des données, lineage, documentation | | ✔ |
| Split temporel, entraînement, évaluation | ✔ | |
| Inférence, calibration, explicabilité | ✔ | |

---

## Les couches

```
football-data.org
      │  src/ingestion/fetch_matches.py
      ▼
S3  raw/{code}/{date}/matches.json          zone brute, immuable
      │  src/transform/process_matches.py
      ▼
S3  curated/{code}/{season}/matches.parquet catalogué dans Glue, table `matches`
      │
      ▼  ────────────────────────────── dbt ──────────────────────────────
      │
   stg_matches                          typage · nettoyage · déduplication
      │
      ├─▶ int_team_match_results         grain équipe × match · chronologie
      │        │
      │        ├─▶ int_team_form         forme glissante, toutes rencontres
      │        └─▶ int_home_away_form    forme glissante, domicile / extérieur
      │                 │
      ├─────────────────┴─▶ fct_match_features       mart ML
      │
      └────────────────────▶ mart_league_overview    marts analytics
                             mart_matchweek_goals
                             mart_team_form
      │
      ▼  ──────────────────────────────────────────────────────────────────
scripts/export_marts.py  →  data/marts/*.parquet
      │                                   │
      ▼                                   ▼
src/ml (entraînement, inférence)     app.py (Streamlit)
```

### RAW → STAGING

`stg_matches` est la seule porte d'entrée. Elle type et renomme, écarte ce qui
ne peut pas être un match (identifiant, date ou équipe manquante, équipe
opposée à elle-même), recalcule le résultat H/D/A depuis le score — une seule
règle dans tout le projet — et **déduplique**.

La déduplication n'est pas décorative : la zone curated est réécrite en
relisant l'intégralité de `raw/`, donc rejouer l'ingestion sur les mêmes
partitions y laisse des copies. Au moment de l'écriture, `curated/PL/2025/`
contenait 760 lignes pour 380 matchs de Premier League. `stg_matches` garde
une ligne par `match_id`, en préférant la version la plus avancée du match
(jouée avant programmée, puis la plus récente), et le test singulier
`assert_staging_keeps_every_source_match` vérifie qu'aucun match n'a été perdu
au passage.

La colonne `venue` n'est pas reprise : elle existe dans la zone curated mais
est vide sur 100 % des lignes.

### STAGING → INTERMEDIATE

`int_team_match_results` fait passer du grain « match » au grain « équipe ×
match » : un match produit deux lignes, une par équipe, avec buts pour, buts
contre, issue et points de son point de vue.

```
match 100 : PSG 3 - 1 Lyon
→  PSG  | Lyon | HOME | 3 | 1 | WIN  | 3 pts
   Lyon | PSG  | AWAY | 1 | 3 | LOSS | 0 pt
```

Le modèle porte aussi deux compteurs de chronologie, `prior_played_matches` et
`prior_played_matches_same_side` : le nombre de matchs **joués** strictement
avant la ligne courante. Ils sont définis pour toute ligne, jouée ou non — ce
sont eux qui rendent la construction des features exacte (voir plus bas).

`int_team_form` et `int_home_away_form` calculent ensuite la forme sur les cinq
derniers matchs joués : la première toutes rencontres confondues, la seconde
séparément à domicile et à l'extérieur. Ce sont les colonnes de la seconde que
le modèle consomme : ce qu'une équipe fait en déplacement explique mieux un
déplacement que sa forme générale.

### INTERMEDIATE → MARTS

`fct_match_features` est le contrat ML (section suivante).

Les trois marts analytics remplacent chacun du code qui existait ailleurs :

| Mart | Grain | Remplace |
|---|---|---|
| `mart_league_overview` | compétition × saison | `queries/home_advantage.sql` et les KPI recalculés dans `app.py` |
| `mart_matchweek_goals` | compétition × saison × semaine | `queries/avg_goals_per_round.sql` et l'agrégation ISO-semaine d'`app.py` |
| `mart_team_form` | équipe × saison | `queries/top_scorers.sql`, `compute_standings()` et `build_prediction_row()` |

---

## Le contrat ML : `fct_match_features`

Une ligne par match. À gauche les identifiants et la profondeur d'historique,
au milieu les features d'avant-match, à droite la cible.

`src/ml/features.py` ne fait que traduire six colonnes du mart en les six
entrées attendues par les modèles versionnés (plus `home_advantage`, constante
à 1) :

| Feature du modèle | Colonne du mart |
|---|---|
| `home_form` | `home_home_avg_points_last_5` |
| `away_form` | `away_away_avg_points_last_5` |
| `home_goals_avg` | `home_home_avg_goals_for_last_5` |
| `away_goals_avg` | `away_away_avg_goals_for_last_5` |
| `home_conceded_avg` | `home_home_avg_goals_against_last_5` |
| `away_conceded_avg` | `away_away_avg_goals_against_last_5` |

Le mart expose une trentaine d'autres colonnes — forme globale, bilan sur cinq
matchs, différence de buts, nombre de victoires/nuls/défaites — disponibles
pour une itération future du modèle sans retoucher au SQL.

Les colonnes préfixées `target_` (`target_result`, `target_home_goals`,
`target_away_goals`) ne sont connues qu'après le coup de sifflet final. Le
préfixe permet de les exclure d'un geste ; aucune feature n'en dérive.

**Parité vérifiée.** Sur les 1 751 matchs communs, les six features issues du
SQL sont identiques à 1e-9 près à celles que produisait l'ancien
`compute_features()` en pandas. Le mart contient un match de plus : la
rencontre `AWARDED` (résultat attribué sur tapis vert) que le filtre
`status == "FINISHED"` écartait, alors qu'elle a un score définitif et compte
au classement.

---

## Absence de fuite temporelle

C'est l'exigence centrale : le modèle prédit un match futur, donc aucune
feature ne doit contenir le résultat du match en cours, ni quoi que ce soit
d'un match postérieur.

### Le mécanisme

`int_team_form` décrit l'état d'une équipe **après** son n-ième match joué : la
fenêtre inclut le match n. Ce n'est pas là que la fuite est empêchée.

Elle l'est par une jointure. Pour le match M d'une équipe :

```
forme retenue = la ligne de forme dont le rang (played_seq) vaut
                le nombre de matchs joués strictement AVANT M
                (prior_played_matches)
```

et `prior_played_matches` est calculé par une fenêtre qui exclut explicitement
la ligne courante :

```sql
sum(case when is_played then 1 else 0 end) over (
    partition by team, competition_code, season
    order by match_date, match_id
    rows between unbounded preceding and 1 preceding
)
```

Le match M n'entre donc jamais dans sa propre fenêtre, et aucun match
postérieur ne peut y entrer puisque les rangs suivent l'ordre chronologique.

### Pourquoi passer par un rang plutôt qu'une fenêtre `5 preceding and 1 preceding`

Une fenêtre par lignes posée directement sur le match compterait *des lignes*,
pas *des matchs joués*. Un match reporté, ou une rencontre à venir intercalée
dans le calendrier, occuperait une place dans la fenêtre sans y apporter de
résultat, et la forme serait calculée sur quatre matchs au lieu de cinq sans
que rien ne le signale. Le rang, lui, ne compte que du joué.

Le même mécanisme donne gratuitement une forme d'avant-match aux rencontres
**non encore jouées** : le compteur est défini pour toute ligne, donc un match
programmé reçoit la forme qui suit le dernier match joué de chaque équipe.

### Les cas limites, un par un

| Cas | Traitement |
|---|---|
| Matchs le même jour, horodatage identique | Le tri est `(match_date, match_id)` : total et déterministe. Deux exécutions donnent le même ordre, donc les mêmes fenêtres et la même frontière de split. |
| Match reporté puis rejoué | La déduplication garde la version jouée, qui porte la date effective. La chronologie suit la date à laquelle le match s'est joué. |
| Match non joué au milieu du calendrier | Ne consomme aucun rang : `played_seq` est NULL, les compteurs ne l'incrémentent pas. |
| Début de saison | La fenêtre est partitionnée par `(équipe, compétition, saison)` : elle ne franchit jamais une frontière de saison. Les premiers matchs ont une fenêtre plus courte, `matches_in_window` le dit. |
| Promu, aucun historique | `prior_played_matches = 0`, aucune ligne de forme correspondante, features NULL. |
| Historique insuffisant (1 à 4 matchs) | Fenêtre partielle, moyennes calculées sur ce qui existe, `matches_in_window` porte la profondeur réelle. |

### Ce qui n'est jamais fait

Aucune valeur manquante n'est imputée à zéro. Un zéro se confondrait avec
« a joué et n'a pris aucun point » — c'est-à-dire avec la pire forme possible,
attribuée par erreur à une équipe dont on ne sait rien. Les features restent
NULL, `*_matches_played` dit pourquoi, et le tri des lignes exploitables
appartient au consommateur : `training_frame()` les écarte de l'entraînement.

### Les tests qui le vérifient

| Test | Ce qu'il attrape |
|---|---|
| `assert_no_future_information_in_features` | Recalcule, à partir de l'historique brut et par une jointure sur les dates seules, la moyenne de points qu'aurait dû avoir chaque fenêtre. Chemin de calcul indépendant de celui du mart : une fuite ou un rattachement décalé apparaît comme un écart. |
| `fct_match_features_home_form_predates_kickoff` | `home_form_as_of < match_date`, sur chaque ligne. Idem côté extérieur. |
| `fct_match_features_no_history_means_null_features` | Une équipe sans historique n'a pas de features inventées. |
| `assert_features_present_whenever_history_exists` | Le symétrique : une jointure cassée produirait des NULL partout sans lever d'erreur, et le pipeline entraînerait sur du vide en silence. |
| `tests/test_marts.py::TestExportedContract` | Les mêmes invariants, rejoués côté Python sur le Parquet versionné — c'est lui que lit le dashboard déployé. |

---

## Matérialisations

| Couche | Choix | Pourquoi |
|---|---|---|
| `staging` | `view` | La zone curated tient dans quelques mégaoctets. La matérialiser coûterait un scan de plus sans rien faire gagner. |
| `intermediate` | `table` | Chaque modèle est relu deux à quatre fois en aval (features domicile, features extérieur, marts analytics). Le matérialiser une fois coûte moins cher que recalculer la fenêtre à chaque `ref()`. |
| `marts` | `table` | Ce sont les artefacts consommés hors dbt. |

**Pas de modèle incremental.** Une saison des cinq grands championnats fait
~1 750 matchs, soit moins d'un mégaoctet de Parquet : un `dbt build` complet
scanne moins que le minimum facturé par Athena. Un modèle incremental
apporterait ici une `unique_key`, une gestion des matchs corrigés a posteriori
et un risque de dérive silencieuse entre exécutions, pour aucun gain mesurable.
Le seuil à partir duquel la question se repose : plusieurs saisons × plusieurs
compétitions, quand un rafraîchissement complet dépasse la dizaine de
secondes ou quand la fenêtre de recalcul devient plus coûteuse que le suivi
d'état.

Toutes les couches sont matérialisées dans le même schéma
(`football_analytics_dev` en développement, `football_analytics` en
production). Le préfixe du modèle — `stg_` / `int_` / `fct_` / `mart_` — porte
déjà la couche, et un schéma unique évite d'exiger un `glue:CreateDatabase` par
couche.

---

## Qualité des données

138 tests s'exécutent à chaque `dbt build`. Ils se répartissent en quatre
familles.

**Structure.** `unique` et `not_null` sur les clés primaires,
`unique_combination_of_columns` sur les modèles à clé composite,
`relationships` de `fct_match_features` et `int_team_match_results` vers
`stg_matches`.

**Domaine.** `accepted_values` sur `competition_code`, `result` / `target_result`
(H/D/A), `home_away` (HOME/AWAY), `outcome` (WIN/DRAW/LOSS). `accepted_range`
sur les grandeurs bornées : une moyenne de points est entre 0 et 3, une fenêtre
compte entre 1 et 5 matchs, un pourcentage est entre 0 et 100.

**Cohérence métier.** Les tests qui attrapent une erreur de calcul plutôt
qu'une erreur de saisie : `points = wins * 3 + draws`,
`home_wins + draws + away_wins = matches_played`,
`form_wins + form_draws + form_losses = matches_in_window`,
`home_matches_played + away_matches_played = matches_played`,
`total_goals = home_goals + away_goals`, buts jamais négatifs, une équipe ne
joue jamais contre elle-même, un match joué a toujours un résultat.

**Temporalité.** Les quatre tests de la section précédente.

La source elle-même est testée en `not_null` et `accepted_values`, mais **pas**
en `unique` sur `match_id` : les doublons y sont attendus, c'est le rôle de
`stg_matches` de les retirer. Un test `unique` sur la source échouerait en
décrivant correctement la réalité, ce qui ne rendrait service à personne.

Pas de contrôle de fraîcheur (`freshness`) non plus : la zone curated ne porte
aucun horodatage d'ingestion, seulement la date de coup d'envoi. Un contrôle
posé sur celle-ci mesurerait le calendrier des rencontres, pas l'actualité des
données, et virerait au rouge chaque été. Le préalable est une colonne
`ingested_at` dans le transform Python.

---

## Cibles et environnements

Trois cibles, un seul jeu de modèles.

| Cible | Moteur | Source | Credentials | Usage |
|---|---|---|---|---|
| `dev` | DuckDB | `data/cache/matches_all_*.parquet` (instantané versionné) | aucun | Développement local, CI |
| `dev_s3` | DuckDB | `s3://…/curated/*/*/matches.parquet` | S3 lecture | Valider les modèles sur les données réelles sans droits Athena/Glue |
| `athena` | Athena | table Glue `football_db.matches` | Athena + Glue + S3 | Production |

Les cibles DuckDB ne sont pas un jouet : elles exécutent les mêmes modèles et
les mêmes 138 tests, sur les mêmes données. C'est ce qui permet à la CI de
vérifier réellement la couche de qualité à chaque commit, sans credentials ni
facture Athena.

Le SQL est écrit pour tourner sur les deux moteurs. Deux précautions en
découlent, visibles dans les modèles :

- **Pas de `QUALIFY`** — un `row_number()` dans une CTE puis un `where`.
  DuckDB accepte `QUALIFY`, Athena selon la version du moteur ; l'écriture
  portable ne coûte rien.
- **`cast(x as double)` avant chaque division.** Sur Trino, diviser deux
  entiers donne un entier ; sur DuckDB, non. Sans cast, la même requête
  donnerait deux résultats différents selon la cible.

Le fuseau de la connexion DuckDB est forcé à UTC dans `profiles.yml` : les
horodatages curated sont en UTC, et sans ce réglage un `CAST` les convertirait
dans le fuseau de la machine, rendant les fenêtres non reproductibles d'un
poste à l'autre.

### Limites connues

- **Le SQL Athena n'est pas exécuté en CI.** `dbt parse --target athena` valide
  le projet contre l'adaptateur de production — profil, sources, `ref()`,
  macros, Jinja — mais `dbt compile` demande `glue:GetTables` pour résoudre la
  source, donc des credentials AWS. Une divergence de dialecte entre DuckDB et
  Trino se verrait au premier `dbt build --target athena`, pas avant.
- **La cible `athena` n'a pas été exécutée** lors de la mise en place : le
  compte IAM du projet dispose de S3 en lecture/écriture mais d'aucun droit
  Athena ni Glue. Les modèles ont été validés sur les données réelles via la
  cible `dev_s3`, qui lit exactement les mêmes fichiers Parquet que la table
  Glue.

---

## Commandes

Toutes se lancent **depuis la racine du dépôt** : dbt ne change pas de
répertoire de travail, et les chemins relatifs du profil comme des sources sont
résolus depuis là.

```bash
# Environnement isolé (dbt épingle ses propres jinja2 / click / protobuf)
python -m venv .venv-dbt
.venv-dbt/Scripts/activate            # Windows
source .venv-dbt/bin/activate         # Linux / macOS
pip install -r requirements-dbt.txt

export DBT_PROFILES_DIR=$PWD/dbt      # $env:DBT_PROFILES_DIR = "$PWD\dbt" sous PowerShell

dbt deps    --project-dir dbt                  # dbt_utils
dbt debug   --project-dir dbt --target dev     # vérifie la connexion
dbt parse   --project-dir dbt --target athena  # valide le projet, sans AWS
dbt compile --project-dir dbt --target dev     # SQL compilé sous dbt/target/
dbt build   --project-dir dbt --target dev     # modèles + tests
dbt test    --project-dir dbt --target dev     # tests seuls
dbt docs generate --project-dir dbt --target dev
dbt docs serve    --project-dir dbt

# Sur les données réelles de la zone curated (accès S3 en lecture)
DBT_SOURCE_MATCHES='s3://<bucket>/curated/*/*/matches.parquet' \
  dbt build --project-dir dbt --target dev_s3

# Production
dbt build --project-dir dbt --target athena
```

Puis, pour rendre les marts consommables hors entrepôt :

```bash
python scripts/export_marts.py --source duckdb   # depuis un build dev
python scripts/export_marts.py                   # depuis Athena
```

---

## Prochaines étapes qui vaudraient le coup

- **`matchday` et identifiants d'équipe dans la zone curated.** L'API expose
  `match["matchday"]`, `homeTeam.id` et `awayTeam.id` ; le transform Python ne
  les reprend pas. Avec eux, `mart_matchweek_goals` porterait la vraie journée
  au lieu d'une approximation par semaine calendaire, et les jointures se
  feraient sur des identifiants stables plutôt que sur des noms d'équipe.
- **`ingested_at` dans la zone curated**, préalable à un contrôle de fraîcheur
  qui ait un sens.
- **Partitionner la table Glue** par `competition_code` et `season` quand
  plusieurs saisons seront disponibles : aujourd'hui un scan complet coûte
  moins que le minimum facturé, ce ne sera plus vrai à dix saisons.
