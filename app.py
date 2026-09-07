"""Streamlit dashboard — Football Pipeline (5 grandes ligues européennes)."""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.marts import (
    MART_LEAGUE_OVERVIEW,
    MART_MATCHWEEK_GOALS,
    MART_TEAM_FORM,
    mart_path,
    read_mart,
)
from src.ml.features import fixture_features
from src.ml.inference import load_model, predict_proba
from src.ui import theme

METRICS_PATH = Path("models/metrics.json")

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
# Design system — tout vient de src/ui/theme.py, rien n'est écrit en dur ici
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(theme.css(), unsafe_allow_html=True)

C = theme.COLOR

# ─────────────────────────────────────────────────────────────────────────────
# Data & model
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data
def load_mart(name: str) -> pd.DataFrame:
    """Un mart dbt exporté, ou un DataFrame vide s'il n'a pas encore été produit."""
    try:
        return read_mart(name)
    except FileNotFoundError:
        return pd.DataFrame()


def _league_key(league: str) -> str:
    return "all" if league in ("All", "Toutes") else league


@st.cache_resource
def get_model(league: str):
    """Charge le modèle pré-entraîné de la ligue (mis en cache par session)."""
    return load_model(_league_key(league))


@st.cache_data
def load_metrics() -> dict:
    """Toutes les métriques mesurées hors-ligne, par ligue."""
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text())


def get_league_metrics(league: str) -> dict | None:
    """Lit accuracy/baseline/gain mesurés hors-ligne pour la ligue donnée."""
    return load_metrics().get(_league_key(league))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


# Colonnes de mart_team_form selon le mode d'affichage. Le classement n'est
# plus recalculé ici : le mart porte déjà les trois découpages, il ne reste
# qu'à choisir le bon jeu de colonnes et à les renommer pour le tableau.
_STANDINGS_COLUMNS: dict[str, dict[str, str]] = {
    "both": {
        "J": "matches_played",
        "G": "wins",
        "N": "draws",
        "P": "losses",
        "BP": "goals_for",
        "BC": "goals_against",
        "Diff": "goal_difference",
        "Pts": "points",
    },
    "home": {
        "J": "home_matches_played",
        "G": "home_wins",
        "N": "home_draws",
        "P": "home_losses",
        "BP": "home_goals_for",
        "BC": "home_goals_against",
        "Diff": "home_goal_difference",
        "Pts": "home_points",
    },
    "away": {
        "J": "away_matches_played",
        "G": "away_wins",
        "N": "away_draws",
        "P": "away_losses",
        "BP": "away_goals_for",
        "BC": "away_goals_against",
        "Diff": "away_goal_difference",
        "Pts": "away_points",
    },
}


def build_standings(team_form: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Met mart_team_form au format attendu par `_standings_html`."""
    columns = _STANDINGS_COLUMNS[mode]
    standings = pd.DataFrame({"Équipe": team_form["team"].to_numpy()})
    for label, source in columns.items():
        standings[label] = team_form[source].fillna(0).astype(int).to_numpy()
    ranked = standings.sort_values(["Pts", "Diff", "BP"], ascending=False)
    return ranked.reset_index(drop=True)


def _standings_html(standings: pd.DataFrame, per90: bool = False) -> str:
    """Le classement, dans la typographie du dashboard.

    Streamlit rend `st.dataframe` avec sa propre grille, qui ignore le thème :
    police, couleurs et bordures lui échappent. Ce tableau est donc écrit à la
    main pour rester dans la charte, au prix de perdre le tri interactif —
    l'ordre au classement est de toute façon le seul qui compte ici.
    """
    cols = (
        ["GF/90", "GA/90", "+/−/90"] if per90 else ["GF", "GA", "+/−"]
    )
    thead = (
        "<thead><tr>"
        '<th class="l" style="padding-left:0">#</th>'
        "<th></th>"
        '<th class="l">Team</th>'
        "<th>M</th><th>W</th><th>D</th><th>L</th>"
        f"<th>{cols[0]}</th><th>{cols[1]}</th><th>{cols[2]}</th><th>Pts</th>"
        "</tr></thead>"
    )

    rows_html: list[str] = []
    for i, row in standings.iterrows():
        rank = i + 1
        rank_cls = "rank-1" if rank == 1 else "rank-cell"
        crest = TEAM_CRESTS.get(row["Équipe"], "")
        img = (
            f'<img style="width:26px;height:26px;object-fit:contain;opacity:0.85;'
            f'vertical-align:middle" src="{crest}" alt="" loading="lazy">'
            if crest
            else ""
        )
        played = int(row["J"]) or 1
        if per90:
            gf = f'{row["BP"] / played:.2f}'
            ga = f'{row["BC"] / played:.2f}'
            d = row["Diff"] / played
            diff_str = f"{d:+.2f}"
        else:
            gf = f'{int(row["BP"])}'
            ga = f'{int(row["BC"])}'
            diff_str = f'{int(row["Diff"]):+d}'
        rows_html.append(
            f'<tr>'
            f'<td class="{rank_cls}">{rank}</td>'
            f'<td class="logo">{img}</td>'
            f'<td class="l">{row["Équipe"]}</td>'
            f'<td class="num">{row["J"]}</td>'
            f'<td class="num">{row["G"]}</td>'
            f'<td class="num">{row["N"]}</td>'
            f'<td class="num">{row["P"]}</td>'
            f'<td class="num">{gf}</td>'
            f'<td class="num">{ga}</td>'
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


def _scorecard_html(metrics: dict, highlight: str | None = None) -> str:
    """Performance du modèle face à la baseline, pour chaque ligue.

    Les ligues où le modèle perd sont affichées dans le même traitement que
    celles où il gagne — c'est le point de la page, pas une note de bas de
    page. Le tri est décroissant, donc l'écart négatif ferme le tableau au
    lieu d'être noyé au milieu.
    """
    rows = [
        (code, m)
        for code, m in metrics.items()
        if code in COMPETITION_NAMES and isinstance(m, dict) and "gain" in m
    ]
    if not rows:
        return ""
    rows.sort(key=lambda kv: kv[1]["gain"], reverse=True)
    max_abs = max(abs(m["gain"]) for _, m in rows) or 1.0
    scale = 76.0 / max_abs

    body = ""
    for code, m in rows:
        gain = float(m["gain"])
        cls = theme.measure_class(gain, tolerance=0.0005)
        width = max(abs(gain) * scale, 1.5)
        left = 80.0 if gain >= 0 else 80.0 - width
        bar = (
            f'<span class="dbar">'
            f'<i style="left:{left:.1f}px;width:{width:.1f}px;'
            f'background:{theme.COLOR[cls]}"></i></span>'
        )
        name = COMPETITION_NAMES.get(code, code)
        if highlight and code == highlight:
            name = f'<span style="color:{C["accent"]}">{name}</span>'
        body += (
            "<tr>"
            f"<td>{name}</td>"
            f'<td class="n">{int(m.get("n_rows", 0)):,}</td>'
            f'<td class="mono">{m["baseline"]:.1%}</td>'
            f'<td class="mono">{m["accuracy"]:.1%}</td>'
            f'<td class="delta {cls}">{gain * 100:+.1f} pts</td>'
            f'<td class="dbar-cell">{bar}</td>'
            "</tr>"
        )

    return (
        '<table class="perf-table"><thead><tr>'
        "<th>Competition</th><th>Test rows</th><th>Naive baseline</th>"
        "<th>Model accuracy</th><th>Gain</th><th></th>"
        "</tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _prob_bar(label: str, prob: float, color: str, predicted: bool) -> str:
    pct = prob * 100
    lbl_cls = "prob-row-label predicted" if predicted else "prob-row-label"
    pct_cls = "prob-pct predicted" if predicted else "prob-pct"
    return (
        f'<div class="prob-row">'
        f'<div class="prob-header">'
        f'<span class="{lbl_cls}">{label}</span>'
        f'<span class="{pct_cls}">{pct:.1f}%</span>'
        f"</div>"
        f'<div class="prob-track">'
        f'<div class="prob-fill" style="width:{pct:.1f}%;background:{color}"></div>'
        f"</div></div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.markdown(
    '<p class="sb-title">Football Pipeline</p>'
    '<p class="sb-sub">2025 / 26 Season</p>'
    '<div class="sb-rule" style="margin-bottom:12px"></div>',
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Standings", "Prediction", "About"],
    label_visibility="collapsed",
)

overview_all = load_mart(MART_LEAGUE_OVERVIEW)
team_form_all = load_mart(MART_TEAM_FORM)
matchweek_all = load_mart(MART_MATCHWEEK_GOALS)

if overview_all.empty or team_form_all.empty:
    st.markdown(
        theme.state_block(
            "No dbt marts to read",
            "This dashboard reads the dbt marts exported as Parquet and needs no "
            "AWS credentials at runtime — but the files have to exist. Expected "
            f"under <code>{mart_path(MART_LEAGUE_OVERVIEW).parent.as_posix()}/</code>. "
            "Generate them with <code>dbt build --project-dir dbt</code> then "
            "<code>python scripts/export_marts.py</code>, which is the only step "
            "that needs AWS access.",
            stop=True,
        ),
        unsafe_allow_html=True,
    )
    st.stop()

codes = sorted(overview_all["competition_code"].dropna().unique().tolist())

st.sidebar.markdown(
    '<div class="sb-rule" style="margin:12px 0 10px"></div>'
    '<p class="sb-label">Competition</p>',
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


def _for_league(frame: pd.DataFrame) -> pd.DataFrame:
    """Restreint un mart à la compétition sélectionnée."""
    if selected_league == "All":
        return frame
    return frame[frame["competition_code"] == selected_league]


overview = _for_league(overview_all)
team_form = _for_league(team_form_all)
matchweek = _for_league(matchweek_all)

_total_m = int(overview_all["matches_played"].sum())
_total_l = int(overview_all["competition_code"].nunique())

st.sidebar.markdown(
    '<div class="sb-rule" style="margin:16px 0 10px"></div>'
    f'<p class="sb-meta">{_total_m:,} matches · {_total_l} leagues</p>',
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

    total = int(overview["matches_played"].sum())
    total_goals = int(overview["goals_scored"].sum())
    pct_h = 100.0 * int(overview["home_wins"].sum()) / total if total else 0.0
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

    scorecard = _scorecard_html(
        load_metrics(),
        highlight=selected_league if selected_league != "All" else None,
    )
    if scorecard:
        st.markdown(
            '<span class="sl">Model vs naive baseline'
            '<span class="sl-note">every league, including where the model '
            'loses</span></span>',
            unsafe_allow_html=True,
        )
        st.markdown(scorecard, unsafe_allow_html=True)
        st.caption(
            "Accuracy measured on a held-out temporal split (80/20, no shuffle). "
            "The naive baseline always predicts the majority class of the "
            "training period. A model that cannot beat it is worth reporting too."
        )

    st.markdown('<span class="sl">Goals per matchweek</span>', unsafe_allow_html=True)

    # mart_matchweek_goals est déjà agrégé par compétition et par semaine ; en
    # vue « toutes compétitions » il reste à recombiner les semaines, ce qui se
    # fait sur les totaux et non sur les moyennes.
    weekly = (
        matchweek.groupby("matchweek_start", as_index=False)[
            ["matches_played", "goals_scored"]
        ]
        .sum()
        .sort_values("matchweek_start")
    )
    weekly["avg_goals"] = weekly["goals_scored"] / weekly["matches_played"]
    weekly = weekly.rename(columns={"matches_played": "n_matches"})
    _iso = pd.to_datetime(weekly["matchweek_start"]).dt.isocalendar()
    weekly["label"] = (
        _iso["year"].astype(int).astype(str)
        + "-W"
        + _iso["week"].astype(int).astype(str).str.zfill(2)
    ).to_numpy()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weekly["label"],
            y=weekly["avg_goals"],
            mode="lines",
            line=dict(color=C["ink"], width=1.5),
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
            arrowcolor=C["line"],
            arrowwidth=1,
            font=dict(family=theme.FONT_PLOTLY["mono"], size=10, color=C["ink_2"]),
            ax=0,
            ay=-28,
            bgcolor="rgba(0,0,0,0)",
        )
    fig.update_layout(
        **theme.plotly_layout(
            height=260,
            xaxis=dict(
                gridcolor="rgba(0,0,0,0)",
                linecolor=C["line"],
                tickcolor=C["ink_3"],
                zeroline=False,
                nticks=9,
                tickangle=0,
                title=None,
            ),
            yaxis=dict(
                gridcolor=C["line_2"],
                linecolor="rgba(0,0,0,0)",
                tickcolor=C["ink_3"],
                zeroline=False,
                title=None,
            ),
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<span class="sl">By competition</span>', unsafe_allow_html=True)

    rows_html = ""
    for code in ["PL", "FL1", "BL1", "SA", "PD"]:
        r = overview[overview["competition_code"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        rows_html += (
            f"<tr>"
            f'<td>{COMPETITION_NAMES.get(code, code)}</td>'
            f'<td class="mono">{int(r["matches_played"]):,}</td>'
            f'<td class="mono">{int(r["goals_scored"]):,}</td>'
            f'<td class="mono">{float(r["avg_goals_per_match"]):.2f}</td>'
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
    standings = build_standings(team_form, mode_map[mode_label])

    stat_mode = st.radio(
        "Stats",
        ["Raw stats", "Per 90 min"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<span class="sl">Standings</span>', unsafe_allow_html=True)

    st.markdown(
        _standings_html(standings, per90=(stat_mode == "Per 90 min")),
        unsafe_allow_html=True,
    )

    st.markdown('<span class="sl">Top 10 — Goals scored</span>', unsafe_allow_html=True)
    top10 = standings.nlargest(10, "BP")[["Équipe", "BP"]].sort_values("BP")
    # Un seul usage de l'or par figure : la meilleure attaque. Le reste recule.
    colors = [C["ink_3"]] * len(top10)
    if len(colors):
        colors[-1] = C["accent"]
    fig2 = go.Figure(
        go.Bar(
            x=top10["BP"],
            y=top10["Équipe"],
            orientation="h",
            marker=dict(color=colors),
            width=0.55,
            hovertemplate="%{y}: <b>%{x}</b> goals<extra></extra>",
        )
    )
    fig2.update_layout(
        **theme.plotly_layout(
            height=340,
            xaxis=dict(
                gridcolor=C["line_2"],
                linecolor="rgba(0,0,0,0)",
                tickcolor=C["ink_3"],
                zeroline=False,
                title=None,
            ),
            yaxis=dict(
                gridcolor="rgba(0,0,0,0)",
                linecolor="rgba(0,0,0,0)",
                tickcolor="rgba(0,0,0,0)",
                zeroline=False,
                title=None,
            ),
            bargap=0.35,
            margin=dict(l=0, r=0, t=16, b=0),
        )
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

    model = get_model(selected_league)

    if model is None:
        st.markdown(
            theme.state_block(
                f"No trained model for {competition_label}",
                "Models are trained offline and committed as artefacts. Run "
                "<code>python scripts/train_all_models.py</code> to produce them, "
                "then redeploy. Every other competition remains available from "
                "the sidebar.",
                stop=True,
            ),
            unsafe_allow_html=True,
        )
        st.stop()

    metrics = get_league_metrics(selected_league)
    if metrics is not None:
        baseline = metrics["baseline"]
        acc = metrics["accuracy"]
    else:
        # Même définition que celle mesurée à l'entraînement : la part de
        # victoires à domicile sur la compétition, que le mart porte déjà.
        baseline = float(overview["home_win_pct"].mean()) / 100.0
        acc = None

    teams = sorted(team_form["team"].dropna().unique().tolist())

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
        X_pred = fixture_features(team_form, home_team, away_team)
        if X_pred is None:
            st.markdown(
                theme.state_block(
                    "Not enough history for this fixture",
                    "The features are rolling averages over past matches, so a "
                    "team needs a played record before it can be predicted — "
                    "newly promoted sides early in the season often do not have "
                    "one yet. Pick another pairing.",
                ),
                unsafe_allow_html=True,
            )
        else:
            proba = predict_proba(model, X_pred)
            # LABEL_MAP = {"H": 0, "D": 1, "A": 2}
            max_idx = int(proba.argmax())

            # Trois issues, aucune n'est « bonne » ou « mauvaise » : le vert et
            # le rouge diraient le contraire. Seule l'issue prédite prend l'or,
            # les deux autres reculent.
            outcome_labels = ["Home win", "Draw", "Away win"]
            bars_html = "".join(
                _prob_bar(
                    lbl,
                    float(proba[i]),
                    C["accent"] if i == max_idx else C["ink_3"],
                    i == max_idx,
                )
                for i, lbl in enumerate(outcome_labels)
            )
            st.markdown(
                f'<div class="prob-section">{bars_html}</div>',
                unsafe_allow_html=True,
            )

            acc_value = f"{acc:.1%}" if acc is not None else "N/A"
            if acc is not None:
                delta = acc - baseline
                delta_cls = theme.measure_class(delta, tolerance=0.0005)
                delta_html = (
                    f'<div class="acc-delta {delta_cls}">'
                    f"{delta * 100:+.1f} pts vs baseline</div>"
                )
            else:
                delta_html = ""
            st.markdown(
                '<div class="acc-row">'
                f'<div><div class="acc-value">{acc_value}</div>'
                f'<div class="acc-lbl">Model accuracy</div></div>'
                f'<div><div class="acc-value">{baseline:.1%}</div>'
                f'<div class="acc-lbl">Naive baseline</div>'
                f"{delta_html}"
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
