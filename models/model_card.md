# Model Card — Football Match Outcome Predictor

## 1. Model Overview

| | |
|---|---|
| **Name** | `match_predictor_{league}` (un modèle par compétition + un modèle global `all`) |
| **Task** | Classification multiclasse — prédiction du résultat d'un match (Domicile / Nul / Extérieur) |
| **Labels** | `H` = victoire domicile (0), `D` = nul (1), `A` = victoire extérieur (2) |
| **Algorithmes candidats** | Régression logistique (`LogisticRegression`, `max_iter=1000`) vs Forêt aléatoire (`RandomForestClassifier`, `n_estimators=100`) — le meilleur des deux est retenu par compétition sur l'accuracy de test |
| **Date d'entraînement** | 2026-09-07 (voir `models/metrics.json`, champ `trained_at`) |
| **Artefacts** | `models/match_predictor_{PL,FL1,BL1,SA,PD,all}.joblib` + `models/metrics.json` |
| **Reproductible via** | `scripts/train_all_models.py` (s'appuie sur `src/ml/train.py`) |

## 2. Intended Use

**Ce modèle sert à :**
- Démontrer un pipeline ETL → ML → dashboard de bout en bout (ingestion API,
  stockage S3, transformation, entraînement, inférence Streamlit).
- Illustrer une méthodologie correcte de feature engineering temporel
  (anti-leakage) et de validation hors échantillon sur des séries
  chronologiques sportives.
- Fournir une estimation indicative et pédagogique de probabilités
  H/D/A à partir de la forme récente des équipes.

**Ce modèle NE sert PAS à :**
- Un outil d'aide aux paris sportifs ou à toute prise de décision financière.
  Les performances mesurées (section 5) sont proches, voire parfois
  inférieures, à une baseline naïve — le modèle n'a aucune valeur prédictive
  fiable pour un usage réel.
- Une référence d'évaluation de joueurs, d'équipes ou de quoi que ce soit
  au-delà de la démonstration technique.
- Un système de production : il n'y a pas de monitoring de drift, pas de
  ré-entraînement automatisé, pas de garantie de stabilité dans le temps.

## 3. Training Data

- **Source** : API [football-data.org](https://www.football-data.org) (v4),
  endpoint `competitions/{code}/matches`.
- **Compétitions** : 5 championnats européens — Premier League (`PL`),
  Ligue 1 (`FL1`), Bundesliga (`BL1`), Serie A (`SA`), La Liga (`PD`).
- **Saison** : 2025/26.
- **Chemin des données** : S3 `curated/` → dbt (`stg_matches` →
  `int_team_match_results` → `int_team_form` / `int_home_away_form` →
  `fct_match_features`) → export Parquet `data/marts/`.
- **Volume** : 1 752 matchs après déduplication, dont **1 645 lignes
  exploitables** une fois écartées celles dont une équipe n'a pas encore
  d'historique (voir répartition par ligue en section 5).
- **Découpage train/test** : split **temporel 80/20, sans shuffle**
  (`src/ml/train.py::train_model`) — les 20% de matchs les plus récents de
  chaque ensemble servent de test, afin de ne jamais évaluer le modèle sur
  des matchs antérieurs à ceux utilisés pour l'entraîner.

## 4. Features

Calculées en SQL par dbt, dans le mart `fct_match_features`, sur une fenêtre
glissante des **5 derniers matchs** (`form_window = 5`) par équipe, par
compétition et par saison. `src/ml/features.py` ne fait que traduire les
colonnes du mart en entrées du modèle :

| Feature | Description |
|---|---|
| Feature du modèle | Colonne du mart | Description |
|---|---|---|
| `home_form` | `home_home_avg_points_last_5` | Points moyens (3/1/0) du receveur sur ses 5 derniers matchs à domicile |
| `away_form` | `away_away_avg_points_last_5` | Points moyens du visiteur sur ses 5 derniers matchs à l'extérieur |
| `home_goals_avg` | `home_home_avg_goals_for_last_5` | Buts marqués en moyenne par le receveur sur ses 5 derniers matchs à domicile |
| `away_goals_avg` | `away_away_avg_goals_for_last_5` | Buts marqués en moyenne par le visiteur sur ses 5 derniers matchs à l'extérieur |
| `home_conceded_avg` | `home_home_avg_goals_against_last_5` | Buts concédés en moyenne par le receveur sur ses 5 derniers matchs à domicile |
| `away_conceded_avg` | `away_away_avg_goals_against_last_5` | Buts concédés en moyenne par le visiteur sur ses 5 derniers matchs à l'extérieur |
| `home_advantage` | — | Constante = 1 (indicatrice de l'avantage du terrain) |

Le mart expose une trentaine d'autres colonnes de forme — forme globale, bilan
sur 5 matchs, différence de buts — que ces modèles n'utilisent pas encore ;
elles sont documentées dans `dbt/models/marts/ml/ml.yml`.

**Anti-leakage** : la forme d'une équipe pour le match M est la ligne dont le
rang vaut le nombre de matchs qu'elle avait joués *strictement avant* M. Le
match ne peut donc pas entrer dans sa propre fenêtre, et aucun match
postérieur non plus. Deux colonnes du mart, `home_form_as_of` et
`away_form_as_of`, portent la date du dernier match compté : elle est
strictement antérieure au coup d'envoi, et le test dbt
`assert_no_future_information_in_features` la recalcule par un chemin
indépendant à chaque build. Voir `docs/dbt.md`.

## 5. Performance

Mesurée sur le split de test temporel (20% le plus récent), comparée à une
baseline naïve qui prédit systématiquement "victoire à domicile". Source :
`models/metrics.json`.

| Ligue | Modèle retenu | Accuracy | Baseline (toujours H) | Gain | Log loss | Brier | Lignes (n) |
|---|---|---:|---:|---:|---:|---:|---:|
| Premier League (PL) | Logistic Regression | 43.1% | 42.6% | **+0.4 pt** | 1.085 | 0.655 | 360 |
| Ligue 1 (FL1) | Logistic Regression | 46.6% | 46.1% | **+0.5 pt** | 1.056 | 0.642 | 286 |
| Bundesliga (BL1) | Logistic Regression | 46.6% | 43.8% | **+2.8 pt** | 1.080 | 0.651 | 288 |
| Serie A (SA) | Logistic Regression | 48.6% | 38.9% | **+9.7 pt** | 1.057 | 0.637 | 356 |
| La Liga (PD) | Logistic Regression | 49.3% | 48.9% | **+0.3 pt** | 1.009 | 0.605 | 355 |
| Toutes ligues (all) | Logistic Regression | 44.1% | 44.0% | **+0.1 pt** | 1.053 | 0.635 | 1645 |

**Lecture** : seule la Serie A montre un gain net substantiel par rapport au
hasard structurel du football (l'avantage du terrain). Sur les 4 autres
ligues, le modèle apporte un gain marginal — les features de forme récente
captent peu de signal au-delà de ce que la baseline naïve capture déjà. Le log
loss reste juste en dessous de ln(3) ≈ 1.099 : les probabilités affichées sont
à peine plus informatives qu'un tirage uniforme.

**Après le passage des features à dbt** : les six features de forme sont
identiques, à 1e-9 près, à celles que produisait pandas sur les 1 751 matchs
communs. Les écarts d'accuracy face à la version précédente (Bundesliga
43.1 % → 46.6 %, toutes ligues 44.7 % → 44.1 %) tiennent à un seul changement :
les lignes sont désormais triées par `(match_date, match_id)` et non par la
seule date, ce qui déplace la frontière du split 80/20 quand plusieurs matchs
partagent le même coup d'envoi — six d'un coup en Bundesliga. Le tri étant
maintenant total, le découpage est reproductible.

## 6. Limitations & Known Issues

- **Une seule saison de données** (2025/26) : aucune validation sur plusieurs
  saisons, donc aucune garantie de stabilité saison après saison.
- **Features simples** : pas de données avancées (xG, possession, forme des
  effectifs, blessures, calendrier, cotes de marché). Le modèle ne voit que
  des moyennes de buts/points sur 5 matchs.
- **Petits échantillons par ligue** : 285 à 360 lignes d'entraînement selon
  la compétition — un split 80/20 temporel laisse un jeu de test d'à peine
  ~57 à ~72 matchs, ce qui rend les écarts d'accuracy peu significatifs
  statistiquement.
- **Gain négatif sur la Bundesliga** (−0.7 pt vs baseline) : le modèle fait
  *moins bien* que la prédiction triviale "toujours victoire à domicile" sur
  cette ligue.
- **Pas de validation croisée temporelle** (walk-forward / expanding window) :
  un seul split 80/20 ne permet pas d'estimer la variance de la performance.
- **Pas de calibration des probabilités** : log loss et score de Brier sont
  désormais mesurés et publiés dans `metrics.json`, mais aucun recalibrage
  (Platt, isotonique) n'est appliqué et aucun diagramme de fiabilité n'est
  produit.
- **Modèle global ("all") entraîné sur des ligues hétérogènes** mélangées
  sans feature d'identification de la compétition autre qu'indirecte (via les
  équipes), ce qui peut diluer des dynamiques propres à chaque championnat.

## 7. How to Reproduce

```bash
dbt build --project-dir dbt --target dev        # construit et teste les modèles
python scripts/export_marts.py --source duckdb  # data/marts/*.parquet
python scripts/train_all_models.py
```

Le dernier script réutilise `src/ml/train.py` pour entraîner un modèle par
ligue (`PL`, `FL1`, `BL1`, `SA`, `PD`) + un modèle global (`all`) à partir du
mart `data/marts/fct_match_features.parquet`, sauvegarde chaque `.joblib` sous
`models/match_predictor_{league}.joblib`, et régénère `models/metrics.json`
avec accuracy, baseline, gain, log loss, score de Brier, modèle retenu, date
d'entraînement et nombre de lignes par ligue.

## 8. Ethical Considerations

- **Ne pas utiliser pour les paris sportifs ou toute décision financière.**
  Ce modèle est un artefact pédagogique illustrant un pipeline ML de bout en
  bout ; ses performances (section 5) sont trop proches du hasard pour avoir
  une quelconque valeur d'aide à la décision sur de l'argent réel.
- **Pas de données personnelles** : seules des statistiques publiques de
  matchs (scores, équipes, dates) sont utilisées — aucune donnée individuelle
  sur les joueurs.
- **Biais structurel reconnu** : la baseline elle-même encode un biais
  d'avantage du terrain ; ce modèle n'a pas vocation à corriger ou neutraliser
  ce biais, seulement à le dépasser marginalement sur certaines ligues.
