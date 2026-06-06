"""Streamlit dashboard — Football Pipeline (5 grandes ligues européennes)."""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
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
    "PD": "La Liga",
}

COMPETITION_FLAGS: dict[str, str] = {
    "PL": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "FL1": "🇫🇷",
    "BL1": "🇩🇪",
    "SA": "🇮🇹",
    "PD": "🇪🇸",
}

TEAM_CRESTS: dict[str, str] = {
    "1. FC Heidenheim 1846": "https://crests.football-data.org/44.png",
    "1. FC Köln": "https://crests.football-data.org/1.png",
    "1. FC Union Berlin": "https://crests.football-data.org/28.png",
    "1. FSV Mainz 05": "https://crests.football-data.org/15.png",
    "AC Milan": "https://crests.football-data.org/98.png",
    "AC Pisa 1909": "https://crests.football-data.org/487.png",
    "ACF Fiorentina": "https://crests.football-data.org/99.png",
    "AFC Bournemouth": "https://crests.football-data.org/bournemouth.png",
    "AJ Auxerre": "https://crests.football-data.org/519.png",
    "AS Monaco FC": "https://crests.football-data.org/548.png",
    "AS Roma": "https://crests.football-data.org/100.png",
    "Angers SCO": "https://crests.football-data.org/532.png",
    "Arsenal FC": "https://crests.football-data.org/57.png",
    "Aston Villa FC": "https://crests.football-data.org/58.png",
    "Atalanta BC": "https://crests.football-data.org/102.png",
    "Athletic Club": "https://crests.football-data.org/77.png",
    "Bayer 04 Leverkusen": "https://crests.football-data.org/3.png",
    "Bologna FC 1909": "https://crests.football-data.org/103.png",
    "Borussia Dortmund": "https://crests.football-data.org/4.png",
    "Borussia Mönchengladbach": "https://crests.football-data.org/18.png",
    "Brentford FC": "https://crests.football-data.org/402.png",
    "Brighton & Hove Albion FC": "https://crests.football-data.org/397.png",
    "Burnley FC": "https://crests.football-data.org/328.png",
    "CA Osasuna": "https://crests.football-data.org/79.png",
    "Cagliari Calcio": "https://crests.football-data.org/104.png",
    "Chelsea FC": "https://crests.football-data.org/61.png",
    "Club Atlético de Madrid": "https://crests.football-data.org/78.png",
    "Como 1907": "https://crests.football-data.org/7397.png",
    "Crystal Palace FC": "https://crests.football-data.org/354.png",
    "Deportivo Alavés": "https://crests.football-data.org/263.png",
    "Eintracht Frankfurt": "https://crests.football-data.org/19.png",
    "Elche CF": "https://crests.football-data.org/285.png",
    "Everton FC": "https://crests.football-data.org/62.png",
    "FC Augsburg": "https://crests.football-data.org/16.png",
    "FC Barcelona": "https://crests.football-data.org/81.png",
    "FC Bayern München": "https://crests.football-data.org/5.png",
    "FC Internazionale Milano": "https://crests.football-data.org/108.png",
    "FC Lorient": "https://crests.football-data.org/525.png",
    "FC Metz": "https://crests.football-data.org/545.png",
    "FC Nantes": "https://crests.football-data.org/543.png",
    "FC St. Pauli 1910": "https://crests.football-data.org/20.png",
    "Fulham FC": "https://crests.football-data.org/63.png",
    "Genoa CFC": "https://crests.football-data.org/107.png",
    "Getafe CF": "https://crests.football-data.org/82.png",
    "Girona FC": "https://crests.football-data.org/298.png",
    "Hamburger SV": "https://crests.football-data.org/7.png",
    "Hellas Verona FC": "https://crests.football-data.org/450.png",
    "Juventus FC": "https://crests.football-data.org/109.png",
    "Le Havre AC": "https://crests.football-data.org/533.png",
    "Leeds United FC": "https://crests.football-data.org/341.png",
    "Levante UD": "https://crests.football-data.org/88.png",
    "Lille OSC": "https://crests.football-data.org/521.png",
    "Liverpool FC": "https://crests.football-data.org/64.png",
    "Manchester City FC": "https://crests.football-data.org/65.png",
    "Manchester United FC": "https://crests.football-data.org/66.png",
    "Newcastle United FC": "https://crests.football-data.org/67.png",
    "Nottingham Forest FC": "https://crests.football-data.org/351.png",
    "OGC Nice": "https://crests.football-data.org/522.png",
    "Olympique Lyonnais": "https://crests.football-data.org/523.png",
    "Olympique de Marseille": "https://crests.football-data.org/516.png",
    "Paris FC": "https://crests.football-data.org/1045.png",
    "Paris Saint-Germain FC": "https://crests.football-data.org/524.png",
    "Parma Calcio 1913": "https://crests.football-data.org/112.png",
    "RB Leipzig": "https://crests.football-data.org/721.png",
    "RC Celta de Vigo": "https://crests.football-data.org/558.png",
    "RC Strasbourg Alsace": "https://crests.football-data.org/576.png",
    "RCD Espanyol de Barcelona": "https://crests.football-data.org/80.png",
    "RCD Mallorca": "https://crests.football-data.org/89.png",
    "Racing Club de Lens": "https://crests.football-data.org/546.png",
    "Rayo Vallecano de Madrid": "https://crests.football-data.org/87.png",
    "Real Betis Balompié": "https://crests.football-data.org/90.png",
    "Real Madrid CF": "https://crests.football-data.org/86.png",
    "Real Oviedo": "https://crests.football-data.org/1048.png",
    "Real Sociedad de Fútbol": "https://crests.football-data.org/92.png",
    "SC Freiburg": "https://crests.football-data.org/17.png",
    "SS Lazio": "https://crests.football-data.org/110.png",
    "SSC Napoli": "https://crests.football-data.org/113.png",
    "SV Werder Bremen": "https://crests.football-data.org/12.png",
    "Sevilla FC": "https://crests.football-data.org/559.png",
    "Stade Brestois 29": "https://crests.football-data.org/512.png",
    "Stade Rennais FC 1901": "https://crests.football-data.org/529.png",
    "Sunderland AFC": "https://crests.football-data.org/71.png",
    "TSG 1899 Hoffenheim": "https://crests.football-data.org/2.png",
    "Torino FC": "https://crests.football-data.org/586.png",
    "Tottenham Hotspur FC": "https://crests.football-data.org/73.png",
    "Toulouse FC": "https://crests.football-data.org/511.png",
    "US Cremonese": "https://crests.football-data.org/457.png",
    "US Lecce": "https://crests.football-data.org/5890.png",
    "US Sassuolo Calcio": "https://crests.football-data.org/471.png",
    "Udinese Calcio": "https://crests.football-data.org/115.png",
    "Valencia CF": "https://crests.football-data.org/95.png",
    "VfB Stuttgart": "https://crests.football-data.org/10.png",
    "VfL Wolfsburg": "https://crests.football-data.org/11.png",
    "Villarreal CF": "https://crests.football-data.org/94.png",
    "West Ham United FC": "https://crests.football-data.org/563.png",
    "Wolverhampton Wanderers FC": "https://crests.football-data.org/76.png",
}

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Football Pipeline",
    page_icon="",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS — Editorial Sports
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=DM+Mono:wght@300;400;500&display=swap');

/* ── Reset & base ── */
*, *::before, *::after {
    font-family: 'DM Sans', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    box-sizing: border-box;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2E2E2E; }

/* ── App background ── */
.stApp,
[data-testid="stAppViewContainer"] > .main,
section.main > div { background: #111111 !important; }
.block-container { padding-top: 2.5rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: #0D0D0D !important;
    border-right: 1px solid #2E2E2E !important;
}

/* ── Sidebar radio — hide the dot, style labels ── */
[data-testid="stSidebar"] [data-baseweb="radio-group"] { gap: 0 !important; }
[data-testid="stSidebar"] [data-baseweb="radio"] {
    padding: 8px 0 8px 16px !important;
    margin: 0 !important;
    border-left: 2px solid transparent !important;
    align-items: center !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) {
    border-left: 2px solid #C8A96E !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-baseweb="radio"] label p,
[data-testid="stSidebar"] [data-baseweb="radio"] label span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    color: #555555 !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) label p,
[data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) label span {
    color: #F5F5F5 !important;
}
/* Hide the radio circle */
[data-testid="stSidebar"] [data-baseweb="radio"] [class*="circle"],
[data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child { display: none !important; }

/* ── Headings ── */
h1 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 2.2rem !important;
    font-weight: 400 !important;
    color: #F5F5F5 !important;
    line-height: 1.15 !important;
    letter-spacing: -0.01em !important;
    margin-bottom: 0 !important;
}
h2, h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.15em !important;
    color: #888888 !important;
    margin: 28px 0 16px !important;
}

/* ── Override Streamlit metrics ── */
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 2.2rem !important;
    font-weight: 400 !important;
    color: #C8A96E !important;
    line-height: 1 !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    color: #888888 !important;
}

/* ── Primary button (Predict) ── */
[data-testid="baseButton-primary"] {
    background: #F5F5F5 !important;
    color: #111111 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    border-radius: 0 !important;
    border: none !important;
    height: 44px !important;
    transition: background 0.12s;
}
[data-testid="baseButton-primary"]:hover { background: #E2E2E2 !important; }

/* ── Dividers ── */
hr {
    border: none !important;
    border-top: 1px solid #2E2E2E !important;
    margin: 28px 0 !important;
}

/* ── Section label ── */
.sl {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #888888;
    margin: 28px 0 16px;
    display: block;
    border-top: 1px solid #2E2E2E;
    padding-top: 20px;
}

/* ── KPI row ── */
.kpi-row {
    display: flex;
    align-items: center;
    border-top: 1px solid #2E2E2E;
    border-bottom: 1px solid #2E2E2E;
    padding: 28px 0;
    margin: 24px 0 32px;
}
.kpi-item { flex: 1; padding: 0 28px; text-align: center; }
.kpi-item:first-child { padding-left: 4px; }
.kpi-divider { width: 1px; height: 48px; background: #2E2E2E; flex-shrink: 0; }
.kpi-value {
    font-family: 'DM Mono', monospace;
    font-size: 2.8rem;
    color: #C8A96E;
    line-height: 1;
    letter-spacing: -0.02em;
}
.kpi-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #888888;
    margin-top: 8px;
}

/* ── League summary ── */
.league-table { width: 100%; border-collapse: collapse; }
.league-table thead th {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #555555;
    padding: 0 0 10px;
    border-bottom: 1px solid #2E2E2E;
    text-align: right;
}
.league-table thead th:first-child { text-align: left; }
.league-table tbody tr:nth-child(even) td { background: #141414; }
.league-table tbody td {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    color: #F5F5F5;
    padding: 10px 0;
    text-align: right;
}
.league-table tbody td:first-child { text-align: left; }
.league-table .mono { font-family: 'DM Mono', monospace; font-size: 0.82rem; color: #888888; }

/* ── Standings table ── */
.standings-wrap { overflow-y: auto; max-height: 680px; }
.standings-table { width: 100%; border-collapse: collapse; }
.standings-table thead tr { border-bottom: 1px solid #2E2E2E; }
.standings-table th {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #555555;
    padding: 0 16px 10px 0;
    text-align: right;
    white-space: nowrap;
}
.standings-table th.l { text-align: left; padding-right: 0; }
.standings-table td {
    padding: 8px 16px 8px 0;
    color: #F5F5F5;
    text-align: right;
    font-size: 0.88rem;
    border-bottom: 1px solid #1A1A1A;
}
.standings-table td.l { text-align: left; padding-right: 0; padding-left: 8px; }
.standings-table td.rank-cell {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    color: #555555;
    text-align: left;
    padding-right: 0;
    width: 28px;
}
.standings-table td.rank-1 {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    color: #C8A96E;
    text-align: left;
    padding-right: 0;
    width: 28px;
}
.standings-table td.pts {
    font-family: 'DM Mono', monospace;
    font-size: 0.88rem;
    color: #F5F5F5;
}
.standings-table td.num {
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    color: #888888;
}
.standings-table td.logo { width: 36px; }
.standings-table tbody tr:hover td { background: #161616; }
.standings-table tbody tr:last-child td { border-bottom: none; }
.standings-table tr.sep td {
    padding: 0;
    border: none;
    height: 0;
}
.standings-table tr.sep td > div {
    border-top: 1px dashed #2E2E2E;
    position: relative;
    height: 1px;
    margin: 6px 0;
}
.standings-table tr.sep .sep-label {
    position: absolute;
    left: 50%;
    top: -8px;
    transform: translateX(-50%);
    background: #111111;
    padding: 0 8px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #555555;
    white-space: nowrap;
}

/* ── Prediction ── */
.pred-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #888888;
    display: block;
    margin-bottom: 6px;
}
.pred-vs {
    font-family: 'DM Serif Display', serif;
    font-style: italic;
    font-size: 1.5rem;
    color: #555555;
    text-align: center;
    padding-top: 24px;
    display: block;
    user-select: none;
}
.pred-crest { text-align: center; margin-top: 10px; }
.pred-crest img {
    width: 54px;
    height: 54px;
    object-fit: contain;
    opacity: 0.85;
}

/* ── Prob bars ── */
.prob-section { margin: 24px 0; }
.prob-row { margin: 16px 0; }
.prob-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 7px;
}
.prob-row-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #888888;
}
.prob-row-label.predicted { color: #C8A96E; }
.prob-pct {
    font-family: 'DM Mono', monospace;
    font-size: 0.88rem;
    color: #F5F5F5;
}
.prob-track { background: #1A1A1A; height: 4px; }
.prob-fill { height: 4px; transition: width 0.4s ease; }

/* ── Accuracy section ── */
.acc-row {
    display: flex;
    gap: 48px;
    margin: 20px 0;
    padding-top: 20px;
    border-top: 1px solid #2E2E2E;
}
.acc-value {
    font-family: 'DM Mono', monospace;
    font-size: 2.4rem;
    color: #F5F5F5;
    line-height: 1;
    letter-spacing: -0.02em;
}
.acc-lbl {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #888888;
    margin-top: 6px;
}
.acc-delta {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    margin-top: 5px;
}
.pos { color: #4CAF7D; }
.neg { color: #E05C5C; }

/* ── About ── */
.about-body {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    color: #888888;
    line-height: 1.7;
    max-width: 680px;
}
.about-body strong { color: #F5F5F5; font-weight: 500; }
.about-link {
    color: #C8A96E;
    text-decoration: underline;
    text-underline-offset: 3px;
    text-decoration-color: rgba(200,169,110,0.4);
}
.about-link:hover { text-decoration-color: #C8A96E; }
.stack-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 48px;
    margin: 16px 0;
}
.stack-row-item { padding: 8px 0; border-bottom: 1px solid #1A1A1A; }
.stack-name { font-family: 'DM Sans', sans-serif; font-size: 0.88rem; color: #F5F5F5; }
.stack-desc { font-family: 'DM Sans', sans-serif; font-size: 0.82rem; color: #555555; margin-top: 1px; }
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Plotly base layout
# ─────────────────────────────────────────────────────────────────────────────

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#888888", family="DM Sans, system-ui", size=11),
    xaxis=dict(gridcolor="#1A1A1A", linecolor="#2E2E2E", tickcolor="#555555"),
    yaxis=dict(gridcolor="#1A1A1A", linecolor="#2E2E2E", tickcolor="#555555"),
    margin=dict(l=0, r=0, t=24, b=0),
    showlegend=False,
)

# ─────────────────────────────────────────────────────────────────────────────
# Data & model
# ─────────────────────────────────────────────────────────────────────────────


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
    if league_filter not in ("Toutes", "All") and "league_code" in df.columns:
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


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


def _standings_html(standings: pd.DataFrame, with_zones: bool) -> str:
    n = len(standings)
    sep_after: dict[int, str] = {}
    if with_zones and n >= 2:
        sep_after[1] = "Champion"

    thead = (
        "<thead><tr>"
        '<th class="l" style="padding-left:0">#</th>'
        "<th></th>"
        '<th class="l">Team</th>'
        "<th>M</th><th>W</th><th>D</th><th>L</th>"
        "<th>GF</th><th>GA</th><th>+/−</th><th>Pts</th>"
        "</tr></thead>"
    )

    rows_html: list[str] = []
    for i, row in standings.iterrows():
        rank = i + 1
        if rank > 1 and (rank - 1) in sep_after:
            rows_html.append(
                '<tr class="sep"><td colspan="11">'
                '<div style="border-top:1px dashed #2E2E2E;position:relative;'
                'height:1px;margin:6px 0">'
                '<span style="position:absolute;right:0;top:-9px;background:#111111;'
                'padding:0 0 0 8px;font-family:\'DM Sans\',sans-serif;font-size:0.65rem;'
                'font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
                'color:#C8A96E;white-space:nowrap">Champion</span></div>'
                "</td></tr>"
            )
        rank_cls = "rank-1" if rank == 1 else "rank-cell"
        crest = TEAM_CRESTS.get(row["Équipe"], "")
        img = (
            f'<img style="width:26px;height:26px;object-fit:contain;opacity:0.85;'
            f'vertical-align:middle" src="{crest}" alt="" loading="lazy">'
            if crest
            else ""
        )
        diff = row["Diff"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        rows_html.append(
            f'<tr>'
            f'<td class="{rank_cls}">{rank}</td>'
            f'<td class="logo">{img}</td>'
            f'<td class="l">{row["Équipe"]}</td>'
            f'<td class="num">{row["J"]}</td>'
            f'<td class="num">{row["G"]}</td>'
            f'<td class="num">{row["N"]}</td>'
            f'<td class="num">{row["P"]}</td>'
            f'<td class="num">{row["BP"]}</td>'
            f'<td class="num">{row["BC"]}</td>'
            f'<td class="num">{diff_str}</td>'
            f'<td class="pts">{row["Pts"]}</td>'
            f"</tr>"
        )

    return (
        '<div class="standings-wrap">'
        f'<table class="standings-table">{thead}<tbody>'
        + "".join(rows_html)
        + "</tbody></table></div>"
    )


def _prob_bar(label: str, prob: float, color: str, predicted: bool) -> str:
    pct = prob * 100
    lbl_cls = "prob-row-label predicted" if predicted else "prob-row-label"
    return (
        f'<div class="prob-row">'
        f'<div class="prob-header">'
        f'<span class="{lbl_cls}">{label}</span>'
        f'<span class="prob-pct">{pct:.1f}%</span>'
        f"</div>"
        f'<div class="prob-track">'
        f'<div class="prob-fill" style="width:{pct:.1f}%;background:{color}"></div>'
        f"</div></div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.markdown(
    '<p style="font-family:\'DM Serif Display\',serif;font-size:1.15rem;'
    'font-weight:400;color:#F5F5F5;margin:0 0 2px;line-height:1.2">'
    "Football Pipeline</p>"
    '<p style="font-family:\'DM Sans\',sans-serif;font-size:0.65rem;'
    'font-weight:600;text-transform:uppercase;letter-spacing:0.14em;'
    'color:#555555;margin:0 0 16px">2025 / 26 Season</p>',
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    '<div style="border-top:1px solid #2E2E2E;margin-bottom:12px"></div>',
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Standings", "Prediction", "About"],
    label_visibility="collapsed",
)

df = load_data()

if df.empty:
    st.error(
        "No data found at `data/cache/matches_all_2025.parquet`. "
        "Run `python scripts/export_cache.py` to generate the local cache."
    )
    st.stop()

selected_league = "All"
if "league_code" in df.columns:
    codes = sorted(df["league_code"].dropna().unique().tolist())
    st.sidebar.markdown(
        '<div style="border-top:1px solid #2E2E2E;margin:12px 0 10px"></div>'
        '<p style="font-family:\'DM Sans\',sans-serif;font-size:0.62rem;'
        'font-weight:600;text-transform:uppercase;letter-spacing:0.14em;'
        'color:#555555;margin-bottom:6px">Competition</p>',
        unsafe_allow_html=True,
    )
    if page == "Prediction":
        selected_league = st.sidebar.selectbox(
            "Competition",
            codes,
            index=codes.index("PL") if "PL" in codes else 0,
            format_func=lambda x: COMPETITION_NAMES.get(x, x),
            label_visibility="collapsed",
            key="comp_pred",
        )
    else:
        selected_league = st.sidebar.selectbox(
            "Competition",
            ["All"] + codes,
            format_func=lambda x: "All competitions"
            if x == "All"
            else COMPETITION_NAMES.get(x, x),
            label_visibility="collapsed",
            key="comp_all",
        )
    if selected_league != "All":
        df = df[df["league_code"] == selected_league]

finished = df[df["status"] == "FINISHED"].copy()
_full = load_data()
_total_m = int((_full["status"] == "FINISHED").sum())
_total_l = int(_full["league_code"].nunique()) if "league_code" in _full.columns else 5

st.sidebar.markdown(
    '<div style="border-top:1px solid #2E2E2E;margin:16px 0 10px"></div>'
    f'<p style="font-family:\'DM Sans\',sans-serif;font-size:0.68rem;'
    f'color:#555555;margin:0">{_total_m:,} matches · {_total_l} leagues</p>',
    unsafe_allow_html=True,
)

competition_label = (
    COMPETITION_NAMES.get(selected_league, selected_league)
    if selected_league != "All"
    else "Five Major European Leagues"
)


# ─────────────────────────────────────────────────────────────────────────────
# Page 1 — Overview
# ─────────────────────────────────────────────────────────────────────────────

if page == "Overview":
    st.markdown(
        f'<h1>{competition_label}</h1>',
        unsafe_allow_html=True,
    )

    total = len(finished)
    total_goals = int(finished["total_goals"].fillna(0).sum())
    pct_h = float((finished["result"] == "H").mean()) * 100 if total else 0.0
    avg_gpm = total_goals / total if total else 0.0

    kpis = [
        (f"{total:,}", "Matches"),
        (f"{total_goals:,}", "Goals"),
        (f"{pct_h:.1f}%", "Home wins"),
        (f"{avg_gpm:.2f}", "Goals / match"),
    ]
    items = []
    for i, (val, lbl) in enumerate(kpis):
        if i > 0:
            items.append('<div class="kpi-divider"></div>')
        items.append(
            f'<div class="kpi-item">'
            f'<div class="kpi-value">{val}</div>'
            f'<div class="kpi-label">{lbl}</div>'
            f"</div>"
        )
    st.markdown(
        '<div class="kpi-row">' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<span class="sl">Goals per matchweek</span>', unsafe_allow_html=True)

    iso = finished["date"].dt.isocalendar()
    weekly = (
        finished.assign(year=iso["year"].astype(int), week=iso["week"].astype(int))
        .groupby(["year", "week"])["total_goals"]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values(["year", "week"])
        .rename(columns={"mean": "avg_goals", "count": "n_matches"})
    )
    weekly["label"] = (
        weekly["year"].astype(str)
        + "-W"
        + weekly["week"].astype(str).str.zfill(2)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weekly["label"],
            y=weekly["avg_goals"],
            mode="lines",
            line=dict(color="rgba(245,245,245,0.8)", width=1.5),
            hovertemplate="<b>%{y:.2f}</b> goals — %{customdata} matches<extra></extra>",
            customdata=weekly["n_matches"],
        )
    )
    if not weekly.empty:
        peak_i = weekly["avg_goals"].idxmax()
        peak = weekly.loc[peak_i]
        fig.add_annotation(
            x=peak["label"],
            y=peak["avg_goals"],
            text=f'{peak["avg_goals"]:.1f}',
            showarrow=True,
            arrowhead=0,
            arrowcolor="#2E2E2E",
            arrowwidth=1,
            font=dict(family="DM Mono, monospace", size=10, color="#888888"),
            ax=0,
            ay=-28,
            bgcolor="rgba(0,0,0,0)",
        )
    fig.update_layout(
        **_PLOTLY,
        height=240,
        xaxis_tickangle=-45,
        xaxis_title=None,
        yaxis_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)

    if "league_code" in finished.columns:
        st.markdown(
            '<span class="sl">By competition</span>', unsafe_allow_html=True
        )
        lg_stats = (
            finished.groupby("league_code")
            .agg(n=("match_id", "count"), goals=("total_goals", "sum"))
            .reset_index()
        )
        lg_stats["avg"] = (lg_stats["goals"] / lg_stats["n"]).round(2)

        rows_html = ""
        for code in ["PL", "FL1", "BL1", "SA", "PD"]:
            r = lg_stats[lg_stats["league_code"] == code]
            if r.empty:
                continue
            r = r.iloc[0]
            rows_html += (
                f"<tr>"
                f'<td>{COMPETITION_NAMES.get(code, code)}</td>'
                f'<td class="mono">{int(r["n"]):,}</td>'
                f'<td class="mono">{int(r["goals"]):,}</td>'
                f'<td class="mono">{r["avg"]:.2f}</td>'
                f"</tr>"
            )
        st.markdown(
            '<table class="league-table">'
            "<thead><tr>"
            '<th>Competition</th><th>Matches</th><th>Goals</th><th>Avg/match</th>'
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody></table>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Page 2 — Standings
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Standings":
    st.markdown(
        f'<h1>{competition_label}</h1>',
        unsafe_allow_html=True,
    )

    mode_label = st.radio(
        "Filter",
        ["Home + Away", "Home only", "Away only"],
        horizontal=True,
        label_visibility="collapsed",
    )
    mode_map = {"Home + Away": "both", "Home only": "home", "Away only": "away"}
    standings = compute_standings(finished, mode_map[mode_label])

    stat_mode = st.radio(
        "Stats",
        ["Raw stats", "Per 90 min"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<span class="sl">Standings</span>', unsafe_allow_html=True)

    disp = standings.copy()
    disp.insert(0, "Rank", range(1, len(disp) + 1))
    disp["Crest"] = disp["Équipe"].map(TEAM_CRESTS)

    if stat_mode == "Per 90 min":
        played = disp["J"].where(disp["J"] > 0).astype(float)
        disp["GF/90"] = (disp["BP"] / played).round(2)
        disp["GA/90"] = (disp["BC"] / played).round(2)
        disp["+/-/90"] = (disp["Diff"] / played).round(2)
        display_cols = ["Rank", "Crest", "Équipe", "J", "G", "N", "P", "GF/90", "GA/90", "+/-/90", "Pts"]
        col_cfg = {
            "Rank": st.column_config.NumberColumn("#", width="small"),
            "Crest": st.column_config.ImageColumn("", width="small"),
            "Équipe": st.column_config.TextColumn("Team"),
            "J": st.column_config.NumberColumn("M", width="small"),
            "G": st.column_config.NumberColumn("W", width="small"),
            "N": st.column_config.NumberColumn("D", width="small"),
            "P": st.column_config.NumberColumn("L", width="small"),
            "GF/90": st.column_config.NumberColumn("GF/90", format="%.2f", width="small"),
            "GA/90": st.column_config.NumberColumn("GA/90", format="%.2f", width="small"),
            "+/-/90": st.column_config.NumberColumn("+/−/90", format="%.2f", width="small"),
            "Pts": st.column_config.NumberColumn("Pts", width="small"),
        }
    else:
        display_cols = ["Rank", "Crest", "Équipe", "J", "G", "N", "P", "BP", "BC", "Diff", "Pts"]
        col_cfg = {
            "Rank": st.column_config.NumberColumn("#", width="small"),
            "Crest": st.column_config.ImageColumn("", width="small"),
            "Équipe": st.column_config.TextColumn("Team"),
            "J": st.column_config.NumberColumn("M", width="small"),
            "G": st.column_config.NumberColumn("W", width="small"),
            "N": st.column_config.NumberColumn("D", width="small"),
            "P": st.column_config.NumberColumn("L", width="small"),
            "BP": st.column_config.NumberColumn("GF", width="small"),
            "BC": st.column_config.NumberColumn("GA", width="small"),
            "Diff": st.column_config.NumberColumn("+/−", width="small"),
            "Pts": st.column_config.NumberColumn("Pts", width="small"),
        }

    st.dataframe(
        disp[display_cols],
        column_config=col_cfg,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown('<span class="sl">Top 10 — Goals scored</span>', unsafe_allow_html=True)
    top10 = standings.nlargest(10, "BP")[["Équipe", "BP"]].sort_values("BP")
    fig2 = go.Figure(
        go.Bar(
            x=top10["BP"],
            y=top10["Équipe"],
            orientation="h",
            marker=dict(color="#4CAF7D"),
            width=0.55,
            hovertemplate="%{y}: <b>%{x}</b><extra></extra>",
        )
    )
    fig2.update_layout(
        **_PLOTLY,
        height=320,
        xaxis_title=None,
        yaxis_title=None,
        bargap=0.35,
    )
    st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page 3 — Prediction
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Prediction":
    competition_label = COMPETITION_NAMES.get(selected_league, selected_league)

    st.markdown(
        f'<h1>{competition_label} — Prediction</h1>',
        unsafe_allow_html=True,
    )

    with st.spinner("Training model…"):
        model, acc, baseline, df_feat = get_model(selected_league)

    if model is None:
        st.error("Not enough data to train the model for this selection.")
        st.stop()

    teams = sorted(finished["home_team"].dropna().unique().tolist())

    col1, vs_col, col2 = st.columns([5, 2, 5])
    with col1:
        st.markdown('<span class="pred-label">Home</span>', unsafe_allow_html=True)
        home_team = st.selectbox("Home team", teams, label_visibility="collapsed")
        home_crest = TEAM_CRESTS.get(home_team)
        if home_crest:
            st.markdown(
                f'<div class="pred-crest"><img src="{home_crest}" alt="{home_team}"></div>',
                unsafe_allow_html=True,
            )
    with vs_col:
        st.markdown('<span class="pred-vs">vs</span>', unsafe_allow_html=True)
    with col2:
        st.markdown('<span class="pred-label">Away</span>', unsafe_allow_html=True)
        away_options = [t for t in teams if t != home_team]
        away_team = st.selectbox("Away team", away_options, label_visibility="collapsed")
        away_crest = TEAM_CRESTS.get(away_team)
        if away_crest:
            st.markdown(
                f'<div class="pred-crest"><img src="{away_crest}" alt="{away_team}"></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Predict", use_container_width=True, type="primary"):
        X_pred = build_prediction_row(df_feat, home_team, away_team)
        if X_pred is None:
            st.warning(
                "Not enough historical data for one of these teams. "
                "Try a different combination."
            )
        else:
            proba = model.predict_proba(X_pred[FEATURE_COLS].values.astype(float))[0]
            # LABEL_MAP = {"H": 0, "D": 1, "A": 2}
            max_idx = int(proba.argmax())

            outcome_defs = [
                ("Home win", "#4CAF7D"),
                ("Draw", "#888888"),
                ("Away win", "#E05C5C"),
            ]
            bars_html = "".join(
                _prob_bar(lbl, float(proba[i]), color, i == max_idx)
                for i, (lbl, color) in enumerate(outcome_defs)
            )
            st.markdown(
                f'<div class="prob-section">{bars_html}</div>',
                unsafe_allow_html=True,
            )

            delta = acc - baseline
            delta_cls = "pos" if delta >= 0 else "neg"
            delta_str = f"{delta:+.1%}"
            st.markdown(
                '<div class="acc-row">'
                f'<div><div class="acc-value">{acc:.1%}</div>'
                f'<div class="acc-lbl">Model accuracy</div></div>'
                f'<div><div class="acc-value">{baseline:.1%}</div>'
                f'<div class="acc-lbl">Naive baseline</div>'
                f'<div class="acc-delta {delta_cls}">{delta_str} vs baseline</div>'
                f"</div></div>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Logistic Regression vs Random Forest — best model retained. "
                "Temporal 80/20 split, no shuffle."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Page 4 — About
# ─────────────────────────────────────────────────────────────────────────────

elif page == "About":
    st.markdown('<h1>About</h1>', unsafe_allow_html=True)

    st.markdown(
        '<div class="about-body">'
        "<p>This project builds a complete ETL pipeline to analyse and predict "
        "match outcomes across five major European football leagues — "
        "<strong>Premier League</strong>, <strong>Ligue 1</strong>, "
        "<strong>Bundesliga</strong>, <strong>Serie A</strong>, and "
        "<strong>La Liga</strong>.</p>"
        "<p>Raw JSON data is fetched from the "
        '<a class="about-link" href="https://www.football-data.org" target="_blank">'
        "football-data.org</a> API, stored in AWS S3, normalised via "
        "Pandas and AWS Glue into Parquet, and made queryable through "
        "AWS Athena. Machine-learning models (Logistic Regression and "
        "Random Forest) are trained on rolling form features to predict "
        "the result of any fixture.</p>"
        "<p>The pipeline is automated end-to-end with a GitLab CI/CD "
        "configuration covering lint, test, model training, and deployment "
        "stages. This dashboard reads from a pre-built local cache and "
        "requires no AWS credentials at runtime.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<span class="sl">Stack</span>', unsafe_allow_html=True)

    stack = [
        ("Python 3.12", "Core language"),
        ("pandas 2.x", "Data manipulation"),
        ("scikit-learn", "Machine learning"),
        ("Streamlit", "This dashboard"),
        ("Plotly", "Data visualisation"),
        ("PyArrow", "Parquet I/O"),
        ("AWS S3 + Glue", "Storage & transform"),
        ("AWS Athena", "Analytical SQL"),
        ("GitLab CI/CD", "Lint · Test · Deploy"),
    ]
    items_html = "".join(
        f'<div class="stack-row-item">'
        f'<div class="stack-name">{name}</div>'
        f'<div class="stack-desc">{desc}</div>'
        f"</div>"
        for name, desc in stack
    )
    st.markdown(
        f'<div class="stack-grid">{items_html}</div>', unsafe_allow_html=True
    )

    st.markdown(
        '<span class="sl">Links</span>'
        '<div class="about-body" style="margin-top:0">'
        '<a class="about-link" href="https://github.com/AxelCorral/football-pipeline" '
        'target="_blank">GitHub repository</a>'
        " &nbsp;·&nbsp; "
        '<a class="about-link" href="https://www.football-data.org" '
        'target="_blank">football-data.org</a>'
        "</div>",
        unsafe_allow_html=True,
    )
