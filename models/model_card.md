# Model Card — Football Match Outcome Predictor

## 1. Model Overview

| | |
|---|---|
| **Name** | `match_predictor_{league}` (un modèle par compétition + un modèle global `all`) |
| **Task** | Classification multiclasse — prédiction du résultat d'un match (Domicile / Nul / Extérieur) |
| **Labels** | `H` = victoire domicile (0), `D` = nul (1), `A` = victoire extérieur (2) |
| **Algorithmes candidats** | Régression logistique (`LogisticRegression`, `max_iter=1000`) vs Forêt aléatoire (`RandomForestClassifier`, `n_estimators=100`) — le meilleur des deux est retenu par compétition sur l'accuracy de test |
| **Date d'entraînement** | 2026-06-24 (voir `models/metrics.json`, champ `trained_at`) |
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
- **Volume** : ~1750 matchs bruts collectés, dont **1644 lignes exploitables**
  après calcul des features et suppression des lignes sans historique/score
  (voir répartition par ligue en section 5).
- **Découpage train/test** : split **temporel 80/20, sans shuffle**
  (`src/ml/train.py::train_model`) — les 20% de matchs les plus récents de
  chaque ensemble servent de test, afin de ne jamais évaluer le modèle sur
  des matchs antérieurs à ceux utilisés pour l'entraîner.

## 4. Features

Calculées par `src/ml/features.py::compute_features`, sur une fenêtre
glissante des **5 derniers matchs** (`WINDOW = 5`) par équipe :

| Feature | Description |
|---|---|
| `home_form` | Points moyens (3/1/0) de l'équipe à domicile sur ses 5 derniers matchs à domicile |
| `away_form` | Points moyens de l'équipe à l'extérieur sur ses 5 derniers matchs à l'extérieur |
| `home_goals_avg` | Buts marqués en moyenne par l'équipe à domicile sur ses 5 derniers matchs à domicile |
| `away_goals_avg` | Buts marqués en moyenne par l'équipe à l'extérieur sur ses 5 derniers matchs à l'extérieur |
| `home_conceded_avg` | Buts concédés en moyenne par l'équipe à domicile sur ses 5 derniers matchs à domicile |
| `away_conceded_avg` | Buts concédés en moyenne par l'équipe à l'extérieur sur ses 5 derniers matchs à l'extérieur |
| `home_advantage` | Constante = 1 (indicatrice de l'avantage du terrain) |

**Anti-leakage** : chaque moyenne glissante est calculée via
`s.shift(1).rolling(WINDOW, min_periods=1).mean()` — le `shift(1)` garantit
qu'aucune statistique d'un match ne fuite dans ses propres features (le match
courant n'est jamais inclus dans le calcul de sa propre forme).

## 5. Performance

Mesurée sur le split de test temporel (20% le plus récent), comparée à une
baseline naïve qui prédit systématiquement "victoire à domicile". Source :
`models/metrics.json`.

| Ligue | Modèle retenu | Accuracy | Baseline (toujours H) | Gain | Lignes d'entraînement (n) |
|---|---|---:|---:|---:|---:|
| Premier League (PL) | Logistic Regression | 43.1% | 42.6% | **+0.4 pt** | 360 |
| Ligue 1 (FL1) | Logistic Regression | 47.4% | 46.2% | **+1.1 pt** | 285 |
| Bundesliga (BL1) | Logistic Regression | 43.1% | 43.8% | **−0.7 pt** | 288 |
| Serie A (SA) | Logistic Regression | 48.6% | 38.9% | **+9.7 pt** | 356 |
| La Liga (PD) | Logistic Regression | 49.3% | 48.9% | **+0.3 pt** | 355 |
| Toutes ligues (all) | Random Forest | 44.7% | 44.0% | **+0.6 pt** | 1644 |

**Lecture** : seule la Serie A montre un gain net substantiel par rapport au
hasard structurel du football (l'avantage du terrain). Sur les 4 autres
ligues, le modèle apporte un gain marginal voire négatif (Bundesliga) — les
features de forme récente captent peu de signal au-delà de ce que la
baseline naïve capture déjà.

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
- **Pas de calibration des probabilités** vérifiée (Brier score, fiabilité
  diagram) — les probabilités H/D/A affichées dans le dashboard n'ont pas
  été auditées pour leur calibration.
- **Modèle global ("all") entraîné sur des ligues hétérogènes** mélangées
  sans feature d'identification de la compétition autre qu'indirecte (via les
  équipes), ce qui peut diluer des dynamiques propres à chaque championnat.

## 7. How to Reproduce

```bash
python scripts/train_all_models.py
```

Ce script réutilise `src/ml/train.py::train_model` pour entraîner un modèle
par ligue (`PL`, `FL1`, `BL1`, `SA`, `PD`) + un modèle global (`all`) à partir
des caches locaux `data/cache/matches_{LEAGUE}_2025.parquet`, sauvegarde
chaque `.joblib` sous `models/match_predictor_{league}.joblib`, et régénère
`models/metrics.json` avec accuracy, baseline, gain, modèle retenu, date
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
