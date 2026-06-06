"""Streamlit dashboard — Football Pipeline (5 grandes ligues européennes)."""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
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
    page_icon="⚽",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Global ── */
* { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2A2A3A; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3A3A4A; }

/* ── Backgrounds ── */
.stApp, [data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewBlock"] { background: #0A0A0F !important; }
.block-container { padding-top: 2rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0D0D15 !important;
    border-right: 1px solid #2A2A3A !important;
}
[data-testid="stSidebar"] > div { background: #0D0D15 !important; }

/* ── Radio (nav) ── */
[data-testid="stSidebar"] [data-baseweb="radio"] { gap: 6px; }
[data-testid="stSidebar"] [data-baseweb="radio"] label {
    color: #8B8FA8 !important;
    font-size: 0.9rem;
    padding: 6px 8px;
    border-radius: 6px;
    transition: color 0.15s ease;
}
[data-testid="stSidebar"] [data-baseweb="radio"] label:hover { color: #FFFFFF !important; }
[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"] ~ div label,
[data-testid="stSidebar"] [role="radio"][aria-checked="true"] + label {
    color: #00FF87 !important;
}

/* ── Metrics ── */
[data-testid="stMetricValue"] {
    color: #00FF87 !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] { color: #8B8FA8 !important; font-size: 0.82rem !important; }
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Primary button ── */
[data-testid="baseButton-primary"] {
    background: #00FF87 !important;
    color: #0A0A0F !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    border: none !important;
    font-size: 1rem !important;
    letter-spacing: 0.02em;
    transition: background 0.15s ease, transform 0.1s ease;
}
[data-testid="baseButton-primary"]:hover {
    background: #00e67a !important;
    transform: translateY(-1px);
}

/* ── Divider ── */
hr { border-color: #2A2A3A !important; margin: 20px 0 !important; }

/* ── Headers ── */
h1 { font-size: 1.9rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
h2 { font-size: 1.3rem !important; font-weight: 700 !important; color: #FFFFFF !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; color: #FFFFFF !important; }

/* ── KPI cards ── */
.kpi-card {
    background: #12121A;
    border: 1px solid #2A2A3A;
    border-radius: 12px;
    padding: 22px 20px;
    text-align: center;
    transition: border-color 0.2s ease, transform 0.15s ease;
    height: 100%;
}
.kpi-card:hover { border-color: #00FF87; transform: translateY(-2px); }
.kpi-icon { font-size: 1.6rem; margin-bottom: 10px; }
.kpi-value { color: #00FF87; font-size: 2rem; font-weight: 800; line-height: 1.1; }
.kpi-label { color: #8B8FA8; font-size: 0.82rem; margin-top: 6px; letter-spacing: 0.02em; }

/* ── League mini-cards ── */
.league-card {
    background: #12121A;
    border: 1px solid #2A2A3A;
    border-radius: 10px;
    padding: 14px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: border-color 0.2s ease;
}
.league-card:hover { border-color: #00B4FF; }
.league-flag { font-size: 1.5rem; line-height: 1; }
.league-name { color: #FFFFFF; font-weight: 600; font-size: 0.9rem; }
.league-count { color: #8B8FA8; font-size: 0.78rem; margin-top: 2px; }

/* ── Standings table ── */
.standings-wrap { overflow-y: auto; max-height: 640px; border-radius: 10px; }
.standings-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
    background: #12121A;
    border-radius: 10px;
    overflow: hidden;
}
.standings-table thead { position: sticky; top: 0; z-index: 1; }
.standings-table th {
    background: #0D0D15;
    color: #8B8FA8;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 10px 12px;
    border-bottom: 1px solid #2A2A3A;
    text-align: center;
    white-space: nowrap;
}
.standings-table th.col-team { text-align: left; }
.standings-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #1A1A26;
    color: #FFFFFF;
    text-align: center;
    vertical-align: middle;
    white-space: nowrap;
}
.standings-table td.col-team { text-align: left; font-weight: 500; }
.standings-table tr:last-child td { border-bottom: none; }
.standings-table tbody tr:hover td { background: #1A1A26; }
.standings-table .rank { color: #8B8FA8; font-size: 0.82rem; width: 28px; }
.standings-table .pts { color: #00FF87; font-weight: 800; font-size: 0.95rem; }
.standings-table img.crest {
    width: 26px; height: 26px;
    object-fit: contain;
    vertical-align: middle;
}
.zone-cl { border-left: 3px solid #00FF87 !important; }
.zone-el { border-left: 3px solid #00B4FF !important; }
.zone-rel { border-left: 3px solid #FF4757 !important; }
.zone-legend {
    display: flex;
    gap: 18px;
    margin-top: 10px;
    font-size: 0.78rem;
    color: #8B8FA8;
}
.zone-dot {
    display: inline-block;
    width: 10px; height: 10px;
    border-radius: 2px;
    margin-right: 5px;
    vertical-align: middle;
}

/* ── Prob bars ── */
.prob-block { margin: 16px 0; }
.prob-row { margin: 10px 0; }
.prob-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.prob-team { color: #FFFFFF; font-weight: 500; font-size: 0.92rem; }
.prob-pct { color: #FFFFFF; font-weight: 700; font-size: 0.95rem; }
.prob-track {
    background: #1A1A26;
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
}
.prob-fill { height: 8px; border-radius: 4px; transition: width 0.5s ease; }

/* ── VS block ── */
.vs-block {
    text-align: center;
    font-size: 2.2rem;
    font-weight: 900;
    color: #2A2A3A;
    letter-spacing: -0.03em;
    padding-top: 24px;
    user-select: none;
}

/* ── Prediction badge ── */
.pred-result {
    text-align: center;
    padding: 18px;
    border-radius: 12px;
    margin: 12px 0;
}
.pred-badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.02em;
}
.pred-h { background: rgba(0,255,135,0.12); color: #00FF87; border: 1px solid rgba(0,255,135,0.4); }
.pred-d { background: rgba(255,184,0,0.12); color: #FFB800; border: 1px solid rgba(255,184,0,0.4); }
.pred-a { background: rgba(255,71,87,0.12); color: #FF4757; border: 1px solid rgba(255,71,87,0.4); }

/* ── Crest display (prediction) ── */
.team-crest-center { text-align: center; margin: 10px 0 4px; }
.team-crest-center img { width: 60px; height: 60px; object-fit: contain; }

/* ── Timeline ── */
.timeline { padding: 4px 0; }
.tl-step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 6px;
}
.tl-left { display: flex; flex-direction: column; align-items: center; }
.tl-dot {
    width: 38px; height: 38px;
    border-radius: 50%;
    background: #12121A;
    border: 2px solid #00FF87;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
}
.tl-line { width: 2px; flex: 1; min-height: 18px; background: linear-gradient(#00FF87, #2A2A3A); margin: 3px auto; }
.tl-content { padding: 6px 0 16px; }
.tl-title { color: #FFFFFF; font-weight: 600; font-size: 0.92rem; }
.tl-desc { color: #8B8FA8; font-size: 0.82rem; margin-top: 3px; }

/* ── Tech cards ── */
.tech-card {
    background: #12121A;
    border: 1px solid #2A2A3A;
    border-radius: 10px;
    padding: 14px 16px;
    transition: border-color 0.2s ease;
    height: 100%;
}
.tech-card:hover { border-color: #00B4FF; }
.tech-name { color: #FFFFFF; font-weight: 600; font-size: 0.88rem; }
.tech-desc { color: #8B8FA8; font-size: 0.8rem; margin-top: 4px; }

/* ── Link buttons ── */
.link-btn {
    display: inline-block;
    padding: 9px 22px;
    border-radius: 8px;
    background: #12121A;
    border: 1px solid #2A2A3A;
    color: #FFFFFF !important;
    text-decoration: none !important;
    font-weight: 500;
    font-size: 0.9rem;
    transition: border-color 0.2s ease, color 0.2s ease;
    margin-right: 10px;
}
.link-btn:hover { border-color: #00FF87; color: #00FF87 !important; }

/* ── Section title ── */
.section-title {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8B8FA8;
    margin-bottom: 14px;
}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Plotly base layout
# ─────────────────────────────────────────────────────────────────────────────

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", family="system-ui"),
    xaxis=dict(gridcolor="#1A1A26", linecolor="#2A2A3A", zerolinecolor="#2A2A3A"),
    yaxis=dict(gridcolor="#1A1A26", linecolor="#2A2A3A", zerolinecolor="#2A2A3A"),
    margin=dict(l=0, r=0, t=30, b=0),
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
    header = (
        '<thead><tr>'
        '<th class="rank">#</th>'
        '<th></th>'
        '<th class="col-team">Équipe</th>'
        '<th>J</th><th>V</th><th>N</th><th>D</th>'
        '<th>BP</th><th>BC</th><th>+/−</th>'
        '<th>Pts</th>'
        '</tr></thead>'
    )
    rows_html = []
    for i, row in standings.iterrows():
        rank = i + 1
        zone = ""
        if with_zones:
            if rank <= 4:
                zone = "zone-cl"
            elif rank == 5:
                zone = "zone-el"
            elif rank > n - 3:
                zone = "zone-rel"
        crest = TEAM_CRESTS.get(row["Équipe"], "")
        img = f'<img class="crest" src="{crest}" alt="" loading="lazy">' if crest else ""
        diff = row["Diff"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        rows_html.append(
            f'<tr class="{zone}">'
            f'<td class="rank">{rank}</td>'
            f'<td>{img}</td>'
            f'<td class="col-team">{row["Équipe"]}</td>'
            f'<td>{row["J"]}</td>'
            f'<td>{row["G"]}</td>'
            f'<td>{row["N"]}</td>'
            f'<td>{row["P"]}</td>'
            f'<td>{row["BP"]}</td>'
            f'<td>{row["BC"]}</td>'
            f'<td>{diff_str}</td>'
            f'<td class="pts">{row["Pts"]}</td>'
            f'</tr>'
        )
    table = (
        '<div class="standings-wrap">'
        f'<table class="standings-table">{header}<tbody>'
        + "".join(rows_html)
        + "</tbody></table></div>"
    )
    if with_zones:
        legend = (
            '<div class="zone-legend">'
            '<span><span class="zone-dot" style="background:#00FF87"></span>Ligue des Champions (Top 4)</span>'
            '<span><span class="zone-dot" style="background:#00B4FF"></span>Europa League (5e)</span>'
            '<span><span class="zone-dot" style="background:#FF4757"></span>Relégation (3 derniers)</span>'
            "</div>"
        )
        return table + legend
    return table


def _prob_bar(label: str, team_name: str, prob: float, color: str) -> str:
    pct = prob * 100
    suffix = f" — {team_name}" if team_name and team_name != "—" else ""
    return (
        f'<div class="prob-row">'
        f'<div class="prob-header">'
        f'<span class="prob-team">{label}{suffix}</span>'
        f'<span class="prob-pct">{pct:.1f}%</span>'
        f'</div>'
        f'<div class="prob-track">'
        f'<div class="prob-fill" style="width:{pct:.1f}%;background:{color}"></div>'
        f'</div>'
        f'</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.markdown(
    '<p style="font-size:1.35rem;font-weight:800;color:#FFFFFF;margin:0 0 2px">⚽ Football Pipeline</p>',
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    '<hr style="border-color:#2A2A3A;margin:10px 0 14px">',
    unsafe_allow_html=True,
)

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

selected_league = "Toutes"
if "league_code" in df.columns:
    codes = sorted(df["league_code"].dropna().unique().tolist())
    st.sidebar.markdown(
        '<hr style="border-color:#2A2A3A;margin:14px 0 10px">'
        '<p style="color:#8B8FA8;font-size:0.72rem;font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">'
        "Compétition</p>",
        unsafe_allow_html=True,
    )

    def _flag_label(x: str) -> str:
        if x == "Toutes":
            return "🌍  Toutes les compétitions"
        return f"{COMPETITION_FLAGS.get(x, '')}  {COMPETITION_NAMES.get(x, x)}"

    selected_league = st.sidebar.selectbox(
        "Compétition",
        ["Toutes"] + codes,
        format_func=_flag_label,
        label_visibility="collapsed",
    )
    if selected_league != "Toutes":
        df = df[df["league_code"] == selected_league]

st.sidebar.markdown(
    '<hr style="border-color:#2A2A3A;margin:14px 0 10px">'
    '<p style="color:#2A2A3A;font-size:0.72rem;text-align:center">v1.0 · 2025/26</p>',
    unsafe_allow_html=True,
)

finished = df[df["status"] == "FINISHED"].copy()

competition_label = (
    COMPETITION_NAMES.get(selected_league, selected_league)
    if selected_league != "Toutes"
    else "5 Grands Championnats Européens"
)


# ─────────────────────────────────────────────────────────────────────────────
# Page 1 — Vue d'ensemble
# ─────────────────────────────────────────────────────────────────────────────

if page == "Vue d'ensemble":
    st.markdown(
        f'<h1 style="margin-bottom:4px">🏆 {competition_label}</h1>'
        '<p style="color:#8B8FA8;font-size:0.92rem;margin-top:0;margin-bottom:24px">'
        "Pipeline ETL · AWS S3 / Glue / Athena · ML (LR / Random Forest)"
        "</p>",
        unsafe_allow_html=True,
    )

    total = len(finished)
    total_goals = int(finished["total_goals"].fillna(0).sum())
    pct_h = float((finished["result"] == "H").mean()) * 100
    goals_per_match = total_goals / total if total else 0.0

    kpis = [
        ("⚽", f"{total:,}", "Matchs analysés"),
        ("🎯", f"{total_goals:,}", "Buts totaux"),
        ("🏠", f"{pct_h:.1f}%", "Victoires domicile"),
        ("📊", f"{goals_per_match:.2f}", "Buts / match"),
    ]
    cols = st.columns(4)
    for col, (icon, value, label) in zip(cols, kpis):
        col.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-icon">{icon}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-label">{label}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p class="section-title">Buts moyens par semaine ISO</p>',
        unsafe_allow_html=True,
    )

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

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weekly["label"],
            y=weekly["buts_moyens"],
            mode="lines",
            line=dict(color="#00B4FF", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(0,180,255,0.08)",
            hovertemplate="<b>%{y:.2f}</b> buts · %{customdata} matchs<extra></extra>",
            customdata=weekly["nb_matchs"],
        )
    )
    fig.update_layout(
        **_PLOTLY,
        height=280,
        xaxis_tickangle=-45,
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    if "league_code" in finished.columns:
        st.markdown(
            '<p class="section-title" style="margin-top:8px">Par championnat</p>',
            unsafe_allow_html=True,
        )
        league_stats = (
            finished.groupby("league_code")
            .size()
            .reset_index(name="nb_matchs")
        )
        cols5 = st.columns(5)
        for col, code in zip(cols5, ["PL", "FL1", "BL1", "SA", "PD"]):
            row = league_stats[league_stats["league_code"] == code]
            n_m = int(row["nb_matchs"].iloc[0]) if not row.empty else 0
            flag = COMPETITION_FLAGS.get(code, "")
            name = COMPETITION_NAMES.get(code, code)
            col.markdown(
                f'<div class="league-card">'
                f'<span class="league-flag">{flag}</span>'
                f'<div>'
                f'<div class="league-name">{name}</div>'
                f'<div class="league-count">{n_m} matchs</div>'
                f"</div></div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Page 2 — Classement & Performance
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Classement & Performance":
    flag = COMPETITION_FLAGS.get(selected_league, "")
    st.markdown(
        f'<h1 style="margin-bottom:24px">📊 {flag} {competition_label}</h1>',
        unsafe_allow_html=True,
    )

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

    st.markdown(
        '<p class="section-title" style="margin-top:20px">Classement</p>',
        unsafe_allow_html=True,
    )
    with_zones = selected_league != "Toutes"
    st.markdown(_standings_html(standings, with_zones), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p class="section-title">Top 10 — Buts marqués</p>',
        unsafe_allow_html=True,
    )
    top10 = standings.nlargest(10, "BP")[["Équipe", "BP"]].sort_values("BP")
    fig2 = go.Figure(
        go.Bar(
            x=top10["BP"],
            y=top10["Équipe"],
            orientation="h",
            marker=dict(
                color=top10["BP"],
                colorscale=[[0, "#005580"], [1, "#00B4FF"]],
                showscale=False,
            ),
            text=top10["BP"],
            textposition="outside",
            textfont=dict(color="#FFFFFF", size=12),
            hovertemplate="%{y}: <b>%{x}</b> buts<extra></extra>",
        )
    )
    fig2.update_layout(
        **_PLOTLY,
        height=340,
        xaxis_title=None,
        yaxis_title=None,
    )
    st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page 3 — Prédiction
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Prédiction":
    flag = COMPETITION_FLAGS.get(selected_league, "")
    st.markdown(
        f'<h1 style="margin-bottom:24px">🤖 Prédiction — {flag} {competition_label}</h1>',
        unsafe_allow_html=True,
    )

    with st.spinner("Entraînement du modèle…"):
        model, acc, baseline, df_feat = get_model(selected_league)

    if model is None:
        st.error("Impossible d'entraîner le modèle (données insuffisantes).")
        st.stop()

    teams = sorted(finished["home_team"].dropna().unique().tolist())

    col1, vs_col, col2 = st.columns([5, 2, 5])
    with col1:
        home_team = st.selectbox("🏠 Équipe domicile", teams)
        home_crest = TEAM_CRESTS.get(home_team)
        if home_crest:
            st.markdown(
                f'<div class="team-crest-center"><img src="{home_crest}" alt="{home_team}"></div>',
                unsafe_allow_html=True,
            )
    with vs_col:
        st.markdown('<div class="vs-block">VS</div>', unsafe_allow_html=True)
    with col2:
        away_options = [t for t in teams if t != home_team]
        away_team = st.selectbox("✈️ Équipe extérieure", away_options)
        away_crest = TEAM_CRESTS.get(away_team)
        if away_crest:
            st.markdown(
                f'<div class="team-crest-center"><img src="{away_crest}" alt="{away_team}"></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔮 Prédire", use_container_width=True, type="primary"):
        X_pred = build_prediction_row(df_feat, home_team, away_team)
        if X_pred is None:
            st.warning(
                "Pas assez d'historique disponible pour l'une de ces équipes. "
                "Essayez une autre combinaison."
            )
        else:
            proba = model.predict_proba(X_pred[FEATURE_COLS].values.astype(float))[0]
            # LABEL_MAP = {"H": 0, "D": 1, "A": 2}

            max_idx = int(proba.argmax())
            if max_idx == 0:
                badge_label, badge_class = f"{home_team} gagne", "pred-h"
            elif max_idx == 1:
                badge_label, badge_class = "Match nul probable", "pred-d"
            else:
                badge_label, badge_class = f"{away_team} gagne", "pred-a"

            st.markdown(
                f'<div class="pred-result">'
                f'<span style="color:#8B8FA8;font-size:0.85rem">Résultat prédit</span><br>'
                f'<span class="pred-badge {badge_class}">{badge_label}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

            bars = (
                _prob_bar("Victoire domicile", home_team, proba[0], "#00FF87")
                + _prob_bar("Match nul", "—", proba[1], "#FFB800")
                + _prob_bar("Victoire extérieur", away_team, proba[2], "#FF4757")
            )
            st.markdown(
                f'<div class="prob-block">{bars}</div>', unsafe_allow_html=True
            )

            st.markdown(
                '<hr style="border-color:#2A2A3A;margin:20px 0">',
                unsafe_allow_html=True,
            )
            ca, cb = st.columns(2)
            ca.metric("Accuracy du modèle", f"{acc:.1%}")
            cb.metric(
                "Baseline naïve (toujours H)",
                f"{baseline:.1%}",
                delta=f"{acc - baseline:+.1%} vs baseline",
                delta_color="normal",
            )
            st.caption(
                "Logistic Regression vs Random Forest — le meilleur est retenu. "
                "Split temporel 80/20 sans shuffle."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Page 4 — À propos
# ─────────────────────────────────────────────────────────────────────────────

elif page == "À propos":
    st.markdown(
        '<h1 style="margin-bottom:24px">ℹ️ À propos</h1>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="section-title">Pipeline technique</p>',
        unsafe_allow_html=True,
    )

    pipeline = [
        ("🌐", "football-data.org API", "Source JSON — matchs, équipes, compétitions (v4)"),
        ("📦", "AWS S3 raw/", "Stockage brut — un fichier JSON par journée de championnat"),
        ("⚙️", "Pandas / AWS Glue", "Transformation, normalisation et enrichissement Parquet"),
        ("🗄️", "AWS S3 curated/", "Parquet optimisé, partitionné par date (Hive-style)"),
        ("🔍", "AWS Athena", "Requêtes SQL analytiques sur le lac de données"),
        ("🤖", "scikit-learn ML", "LR / Random Forest — prédiction H · D · A"),
        ("📊", "Streamlit", "Ce dashboard — déployé depuis GitHub"),
    ]

    tl_html = '<div class="timeline">'
    for i, (icon, title, desc) in enumerate(pipeline):
        is_last = i == len(pipeline) - 1
        line_html = "" if is_last else '<div class="tl-line"></div>'
        tl_html += (
            f'<div class="tl-step">'
            f'<div class="tl-left"><div class="tl-dot">{icon}</div>{line_html}</div>'
            f'<div class="tl-content">'
            f'<div class="tl-title">{title}</div>'
            f'<div class="tl-desc">{desc}</div>'
            f"</div></div>"
        )
    tl_html += "</div>"
    st.markdown(tl_html, unsafe_allow_html=True)

    st.markdown(
        '<hr style="border-color:#2A2A3A;margin:28px 0 20px">'
        '<p class="section-title">Stack technique</p>',
        unsafe_allow_html=True,
    )

    tech_stack = [
        ("🐍", "Python 3.12", "Langage principal"),
        ("🐼", "pandas 2.x", "Manipulation de données"),
        ("🧠", "scikit-learn", "Machine Learning"),
        ("📈", "Streamlit", "Dashboard interactif"),
        ("📉", "Plotly", "Visualisations"),
        ("🗃️", "PyArrow", "Format Parquet"),
        ("☁️", "AWS S3 / Glue", "Stockage & transformation"),
        ("🔎", "AWS Athena", "SQL analytique"),
        ("🔁", "GitLab CI/CD", "Lint → Test → Deploy"),
    ]

    tcols = st.columns(3)
    for i, (emoji, name, desc) in enumerate(tech_stack):
        tcols[i % 3].markdown(
            f'<div class="tech-card" style="margin-bottom:10px">'
            f'<div class="tech-name">{emoji} {name}</div>'
            f'<div class="tech-desc">{desc}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<hr style="border-color:#2A2A3A;margin:28px 0 20px">'
        '<p class="section-title">Liens</p>'
        '<a class="link-btn" href="https://github.com/AxelCorral/football-pipeline" target="_blank">'
        "🐙 GitHub</a>"
        '<a class="link-btn" href="https://www.football-data.org" target="_blank">'
        "📊 football-data.org</a>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<br><p style="color:#8B8FA8;font-size:0.8rem">'
        "Compétitions : 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League · 🇫🇷 Ligue 1 · 🇩🇪 Bundesliga · 🇮🇹 Serie A · 🇪🇸 La Liga"
        "</p>",
        unsafe_allow_html=True,
    )
