"""Streamlit dashboard — Football Pipeline (5 grandes ligues européennes)."""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.ml.evaluate import baseline_accuracy
from src.ml.features import FEATURE_COLS, compute_features
from src.ml.train import LABEL_MAP, train_model

CACHE_PATH = Path("data/cache/matches_all_2025.parquet")

COMPETITION_NAMES: dict[str, str] = {
    "PL": "Premier League",
    "FL1": "Ligue 1",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "PD": "Primera Division",
}

st.set_page_config(
    page_title="Football Pipeline",
    page_icon="⚽",
    layout="wide",
)


# ── Data & model loading ───────────────────────────────────────────────────────


@st.cache_data
def load_data() -> pd.DataFrame:
    if not CACHE_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(CACHE_PATH)


@st.cache_resource
def _train(_cache_mtime: float, league_filter: str):
    """Entraîne le modèle une seule fois par (fichier, compétition)."""
    df = load_data()
    if df.empty:
        return None, None, None, None
    if league_filter != "Toutes" and "league_code" in df.columns:
        df = df[df["league_code"] == league_filter]
    df_feat = compute_features(df)
    baseline = baseline_accuracy(df)
    _tmp = Path(tempfile.mkdtemp())
    try:
        model, acc, _cm = train_model(df_feat, models_dir=_tmp)
    except ValueError:
        return None, None, baseline, df_feat
    return model, acc, baseline, df_feat


def get_model(league_filter: str = "Toutes"):
    mtime = CACHE_PATH.stat().st_mtime if CACHE_PATH.exists() else 0.0
    return _train(mtime, league_filter)


# ── Helpers ────────────────────────────────────────────────────────────────────


def compute_standings(finished: pd.DataFrame, mode: str) -> pd.DataFrame:
    teams = sorted(
        pd.concat([finished["home_team"], finished["away_team"]]).dropna().unique()
    )
    rows = []
    for team in teams:
        if mode == "home":
            m = finished[finished["home_team"] == team]
            w = int((m["result"] == "H").sum())
            d = int((m["result"] == "D").sum())
            l = int((m["result"] == "A").sum())
            gf = int(m["home_goals"].fillna(0).sum())
            ga = int(m["away_goals"].fillna(0).sum())
        elif mode == "away":
            m = finished[finished["away_team"] == team]
            w = int((m["result"] == "A").sum())
            d = int((m["result"] == "D").sum())
            l = int((m["result"] == "H").sum())
            gf = int(m["away_goals"].fillna(0).sum())
            ga = int(m["home_goals"].fillna(0).sum())
        else:
            hm = finished[finished["home_team"] == team]
            am = finished[finished["away_team"] == team]
            w = int((hm["result"] == "H").sum()) + int((am["result"] == "A").sum())
            d = int((hm["result"] == "D").sum()) + int((am["result"] == "D").sum())
            l = int((hm["result"] == "A").sum()) + int((am["result"] == "H").sum())
            gf = int(hm["home_goals"].fillna(0).sum()) + int(
                am["away_goals"].fillna(0).sum()
            )
            ga = int(hm["away_goals"].fillna(0).sum()) + int(
                am["home_goals"].fillna(0).sum()
            )

        rows.append(
            {
                "Équipe": team,
                "J": w + d + l,
                "G": w,
                "N": d,
                "P": l,
                "BP": gf,
                "BC": ga,
                "Diff": gf - ga,
                "Pts": w * 3 + d,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["Pts", "Diff", "BP"], ascending=False)
        .reset_index(drop=True)
    )


def build_prediction_row(
    df_feat: pd.DataFrame, home_team: str, away_team: str
) -> pd.DataFrame | None:
    home_rows = df_feat[df_feat["home_team"] == home_team].dropna(subset=FEATURE_COLS)
    away_rows = df_feat[df_feat["away_team"] == away_team].dropna(subset=FEATURE_COLS)
    if home_rows.empty or away_rows.empty:
        return None
    h = home_rows.iloc[-1]
    a = away_rows.iloc[-1]
    return pd.DataFrame(
        [
            {
                "home_form": h["home_form"],
                "away_form": a["away_form"],
                "home_goals_avg": h["home_goals_avg"],
                "away_goals_avg": a["away_goals_avg"],
                "home_conceded_avg": h["home_conceded_avg"],
                "away_conceded_avg": a["away_conceded_avg"],
                "home_advantage": 1,
            }
        ]
    )


# ── Sidebar ────────────────────────────────────────────────────────────────────

st.sidebar.title("⚽ Football Pipeline")
page = st.sidebar.radio(
    "Navigation",
    ["Vue d'ensemble", "Classement & Performance", "Prédiction", "À propos"],
    label_visibility="collapsed",
)

df = load_data()

if df.empty:
    st.error(
        "Aucune donnée trouvée dans `data/cache/matches_all_2025.parquet`. "
        "Exécutez `python scripts/export_cache.py` pour générer le cache local."
    )
    st.stop()

# Competition filter — visible dès que la colonne league_code est présente
selected_league = "Toutes"
if "league_code" in df.columns:
    codes = sorted(df["league_code"].dropna().unique().tolist())
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Compétition**")
    selected_league = st.sidebar.selectbox(
        "Compétition",
        ["Toutes"] + codes,
        format_func=lambda x: "Toutes les compétitions"
        if x == "Toutes"
        else COMPETITION_NAMES.get(x, x),
        label_visibility="collapsed",
    )
    if selected_league != "Toutes":
        df = df[df["league_code"] == selected_league]

finished = df[df["status"] == "FINISHED"].copy()

competition_label = (
    COMPETITION_NAMES.get(selected_league, selected_league)
    if selected_league != "Toutes"
    else "5 Grands Championnats Européens"
)


# ── Page 1 — Vue d'ensemble ───────────────────────────────────────────────────

if page == "Vue d'ensemble":
    st.title(f"🏆 {competition_label} — Vue d'ensemble")
    st.markdown(
        "**Problématique :** Prédire le résultat d'un match de football "
        "(victoire domicile · nul · victoire extérieur) à partir de la forme "
        "récente des équipes, via un pipeline ETL complet sur AWS "
        "(S3 → Glue → Athena) et des modèles ML classiques (LR / Random Forest)."
    )

    total = len(finished)
    total_goals = int(finished["total_goals"].fillna(0).sum())
    pct_h = float((finished["result"] == "H").mean()) * 100
    pct_d = float((finished["result"] == "D").mean()) * 100
    pct_a = float((finished["result"] == "A").mean()) * 100

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Matchs joués", f"{total:,}")
    c2.metric("Buts totaux", f"{total_goals:,}")
    c3.metric("% Victoires dom.", f"{pct_h:.1f}%")
    c4.metric("% Nuls", f"{pct_d:.1f}%")
    c5.metric("% Victoires ext.", f"{pct_a:.1f}%")

    st.markdown("---")
    st.subheader("Buts moyens par journée (semaine ISO)")

    iso = finished["date"].dt.isocalendar()
    weekly = (
        finished.assign(year=iso["year"].astype(int), week=iso["week"].astype(int))
        .groupby(["year", "week"])["total_goals"]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values(["year", "week"])
        .rename(columns={"mean": "buts_moyens", "count": "nb_matchs"})
    )
    weekly["label"] = (
        weekly["year"].astype(str)
        + "-S"
        + weekly["week"].astype(str).str.zfill(2)
    )

    fig = px.line(
        weekly,
        x="label",
        y="buts_moyens",
        hover_data={"nb_matchs": True, "label": False},
        labels={
            "label": "Semaine",
            "buts_moyens": "Buts moyens",
            "nb_matchs": "Matchs",
        },
        template="plotly_dark",
    )
    fig.update_traces(line_color="#00d4ff", line_width=2)
    fig.update_layout(xaxis_tickangle=-45, xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)


# ── Page 2 — Classement & Performance ────────────────────────────────────────

elif page == "Classement & Performance":
    st.title(f"📊 {competition_label} — Classement & Performance")

    mode_label = st.radio(
        "Filtrer par :",
        ["Domicile + Extérieur", "Domicile uniquement", "Extérieur uniquement"],
        horizontal=True,
    )
    mode_map = {
        "Domicile + Extérieur": "both",
        "Domicile uniquement": "home",
        "Extérieur uniquement": "away",
    }
    standings = compute_standings(finished, mode_map[mode_label])

    st.markdown("### Classement")
    display = standings.copy()
    display.index = display.index + 1
    st.dataframe(display, use_container_width=True, height=580)

    st.markdown("### Top 10 — Buts marqués")
    top10 = standings.nlargest(10, "BP")[["Équipe", "BP"]].sort_values("BP")
    fig2 = px.bar(
        top10,
        x="BP",
        y="Équipe",
        orientation="h",
        labels={"BP": "Buts marqués", "Équipe": ""},
        template="plotly_dark",
        color="BP",
        color_continuous_scale="Blues",
    )
    fig2.update_layout(coloraxis_showscale=False, yaxis_title=None)
    st.plotly_chart(fig2, use_container_width=True)


# ── Page 3 — Prédiction ───────────────────────────────────────────────────────

elif page == "Prédiction":
    st.title(f"🤖 Prédiction — {competition_label}")

    with st.spinner("Entraînement du modèle…"):
        model, acc, baseline, df_feat = get_model(selected_league)

    if model is None:
        st.error("Impossible d'entraîner le modèle (données insuffisantes).")
        st.stop()

    teams = sorted(finished["home_team"].dropna().unique().tolist())

    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Équipe domicile", teams)
    with col2:
        away_options = [t for t in teams if t != home_team]
        away_team = st.selectbox("✈️ Équipe extérieure", away_options)

    if st.button("🔮 Prédire", use_container_width=True, type="primary"):
        X_pred = build_prediction_row(df_feat, home_team, away_team)
        if X_pred is None:
            st.warning(
                "Pas assez d'historique disponible pour l'une de ces équipes. "
                "Essayez une autre combinaison."
            )
        else:
            proba = model.predict_proba(X_pred[FEATURE_COLS].values.astype(float))[0]
            # LABEL_MAP = {"H": 0, "D": 1, "A": 2} → proba[0]=H, [1]=D, [2]=A
            outcomes = [
                ("Victoire domicile", home_team, proba[0]),
                ("Match nul", "—", proba[1]),
                ("Victoire extérieur", away_team, proba[2]),
            ]

            st.markdown(f"### {home_team} vs {away_team}")
            for label, team, prob in outcomes:
                st.markdown(f"**{label}** {'— ' + team if team != '—' else ''}")
                st.progress(float(prob), text=f"{prob:.1%}")

            st.markdown("---")
            ca, cb = st.columns(2)
            ca.metric("Accuracy du modèle", f"{acc:.1%}")
            cb.metric(
                "Baseline naïve (toujours H)",
                f"{baseline:.1%}",
                delta=f"{acc - baseline:+.1%} vs baseline",
                delta_color="normal",
            )
            st.caption(
                "Le modèle compare Logistic Regression et Random Forest ; "
                "le meilleur est retenu. Split temporel 80/20 sans shuffle."
            )


# ── Page 4 — À propos ─────────────────────────────────────────────────────────

elif page == "À propos":
    st.title("ℹ️ À propos")

    st.markdown("""
## Pipeline technique

Ce projet construit un pipeline ETL complet pour analyser et prédire les résultats
de 5 grands championnats européens de football.

### Compétitions couvertes

| Code | Championnat |
|------|-------------|
| **PL** | Premier League (Angleterre) |
| **FL1** | Ligue 1 (France) |
| **BL1** | Bundesliga (Allemagne) |
| **SA** | Serie A (Italie) |
| **PD** | Primera Division / Liga (Espagne) |

### Architecture AWS

| Composant | Rôle |
|-----------|------|
| **football-data.org API** | Source JSON des matchs |
| **AWS S3 `raw/`** | Stockage des JSON bruts |
| **Pandas / AWS Glue** | Transformation & normalisation Parquet |
| **AWS S3 `curated/`** | Parquet optimisé pour requêtes |
| **AWS Athena** | Requêtes SQL analytiques sur le lac de données |
| **scikit-learn** | Modèles ML (Logistic Regression, Random Forest) |
| **Streamlit** | Dashboard interactif (ce site) |

### CI/CD GitLab

Le pipeline est entièrement automatisé :

```
test   → pytest + coverage ≥ 70 %
lint   → flake8 + black
deploy → aws s3 sync vers le bucket curated
```

### Modèles ML

- **Features** : forme glissante sur 5 matchs (buts marqués/concédés, points, avantage domicile)
- **Split** : temporel 80/20 — aucun shuffle pour respecter l'ordre chronologique
- **Sélection** : le modèle avec la meilleure accuracy test est retenu
- **Labels** : H = victoire domicile · D = nul · A = victoire extérieur

### Liens

- 📁 **Repo** : `gitlab.com/<votre-username>/football-pipeline`
- 📊 **Données** : [football-data.org](https://www.football-data.org)
""")

    st.markdown("---")
    st.markdown("### Stack")
    cols = st.columns(3)
    stack = [
        ("Python 3.12", "Langage principal"),
        ("pandas 2.3", "Manipulation de données"),
        ("scikit-learn", "Machine Learning"),
        ("Streamlit", "Dashboard"),
        ("Plotly", "Visualisations interactives"),
        ("PyArrow", "Format Parquet"),
        ("AWS S3 / Athena", "Storage & Analytics"),
        ("GitLab CI/CD", "Automatisation"),
        ("boto3", "SDK AWS Python"),
    ]
    for i, (name, desc) in enumerate(stack):
        cols[i % 3].markdown(f"**{name}** — {desc}")
