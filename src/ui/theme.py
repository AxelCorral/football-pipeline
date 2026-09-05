"""Système de design du dashboard — source unique de vérité.

Toute couleur, police, taille et graduation d'espacement du dashboard est
définie ici et nulle part ailleurs. Les règles d'usage sont écrites dans
`docs/design.md` ; ce module en est l'implémentation.

Trois familles de couleurs, jamais mélangées :

- **structure** — fonds, filets, encres. Neutres.
- **marque** — l'or `accent`. Une seule utilisation emphatique par vue.
- **mesure** — `better` / `worse` / `even`. Sémantiques : elles ne qualifient
  qu'une valeur comparée à une référence explicite. Jamais un bouton, jamais
  un décor, jamais une série de graphique choisie par commodité.
"""

from __future__ import annotations

from string import Template

# ─────────────────────────────────────────────────────────────────────────────
# Tokens
# ─────────────────────────────────────────────────────────────────────────────

COLOR: dict[str, str] = {
    # structure
    "ground": "#111111",       # fond de page
    "ground_2": "#0D0D0D",     # sidebar
    "surface": "#141414",      # ligne alternée, survol
    "surface_2": "#161616",    # survol de ligne
    "line": "#2E2E2E",         # filet structurant
    "line_2": "#1A1A1A",       # filet interne de tableau
    "ink": "#F5F5F5",          # texte principal
    "ink_2": "#888888",        # texte secondaire
    "ink_3": "#555555",        # étiquette, texte tertiaire
    # marque
    "accent": "#C8A96E",
    "accent_dim": "rgba(200,169,110,0.4)",
    # mesure — sémantique uniquement
    "better": "#4CAF7D",
    "worse": "#E05C5C",
    "even": "#888888",
}

FONT: dict[str, str] = {
    "display": "'DM Serif Display', Georgia, serif",
    "sans": "'DM Sans', system-ui, sans-serif",
    "mono": "'DM Mono', ui-monospace, monospace",
}

# Plotly n'accepte pas les guillemets CSS dans une famille de police.
FONT_PLOTLY: dict[str, str] = {
    "sans": "DM Sans, system-ui",
    "mono": "DM Mono, monospace",
}

# Échelle typographique, en rem. Chaque niveau a un emploi, listé dans docs/design.md.
SIZE: dict[str, str] = {
    "hero": "2.8rem",     # chiffre de KPI
    "h1": "2.2rem",       # titre de page
    "stat": "2.4rem",     # chiffre de mesure
    "body": "0.9rem",
    "table": "0.88rem",
    "num": "0.82rem",
    "meta": "0.78rem",
    "label": "0.7rem",    # étiquette de section
    "micro": "0.65rem",   # étiquette de KPI, en-tête de tableau
    "nano": "0.62rem",
}

# Une seule graduation d'espacement, en px.
SPACE = (4, 8, 12, 16, 20, 28, 40, 56)

# Les trois familles, chargées en une requête.
FONTS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=DM+Serif+Display:ital@0;1"
    "&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400"
    "&family=DM+Mono:wght@300;400;500"
    "&display=swap"
)


def _t(name: str) -> str:
    return COLOR[name]


# ─────────────────────────────────────────────────────────────────────────────
# Feuille de style
# ─────────────────────────────────────────────────────────────────────────────

_CSS_TEMPLATE = Template(
    """
<style>
@import url('$fonts_url');

/* ── Reset & base ── */
*, *::before, *::after {
    font-family: $sans;
    -webkit-font-smoothing: antialiased;
    box-sizing: border-box;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: $line; }

/* ── Mise en page ──
   Le fond de page vient de theme.backgroundColor dans .streamlit/config.toml :
   trois `!important` de moins, et rien à recorriger à la prochaine version. */
.block-container { padding-top: 2.5rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: $ground_2 !important;
    border-right: 1px solid $line !important;
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
    border-left: 2px solid $accent !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-baseweb="radio"] label p,
[data-testid="stSidebar"] [data-baseweb="radio"] label span {
    font-family: $sans !important;
    font-size: 0.85rem !important;
    color: $ink_3 !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) label p,
[data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) label span {
    color: $ink !important;
}
[data-testid="stSidebar"] [data-baseweb="radio"] [class*="circle"],
[data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child { display: none !important; }

/* ── Headings ── */
h1 {
    font-family: $display !important;
    font-size: $s_h1 !important;
    font-weight: 400 !important;
    color: $ink !important;
    line-height: 1.15 !important;
    letter-spacing: -0.01em !important;
    margin-bottom: 0 !important;
}
h2, h3 {
    font-family: $sans !important;
    font-size: $s_label !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.15em !important;
    color: $ink_2 !important;
    margin: 28px 0 16px !important;
}

/* ── Streamlit metrics ── */
[data-testid="stMetricValue"] {
    font-family: $mono !important;
    font-size: $s_h1 !important;
    font-weight: 400 !important;
    color: $accent !important;
    line-height: 1 !important;
}
[data-testid="stMetricLabel"] {
    font-family: $sans !important;
    font-size: $s_micro !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    color: $ink_2 !important;
}

/* ── Primary button (Predict) ── */
[data-testid="baseButton-primary"],
[data-testid="stBaseButton-primary"] {
    background: $ink !important;
    color: $ground !important;
    font-family: $sans !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    border-radius: 0 !important;
    border: none !important;
    height: 44px !important;
    transition: background 0.12s;
}
[data-testid="baseButton-primary"]:hover,
[data-testid="stBaseButton-primary"]:hover { background: #E2E2E2 !important; }
[data-testid="baseButton-primary"]:focus-visible,
[data-testid="stBaseButton-primary"]:focus-visible {
    outline: 2px solid $accent !important;
    outline-offset: 2px !important;
}

/* ── Dividers ── */
hr {
    border: none !important;
    border-top: 1px solid $line !important;
    margin: 28px 0 !important;
}

/* ── Section label ── */
.sl {
    font-family: $sans;
    font-size: $s_label;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: $ink_2;
    margin: 28px 0 16px;
    display: block;
    border-top: 1px solid $line;
    padding-top: 20px;
}
.sl .sl-note {
    text-transform: none;
    letter-spacing: 0;
    font-weight: 400;
    color: $ink_3;
    font-size: $s_meta;
    margin-left: 10px;
}

/* ── KPI row ── */
.kpi-row {
    display: flex;
    align-items: center;
    border-top: 1px solid $line;
    border-bottom: 1px solid $line;
    padding: 28px 0;
    margin: 24px 0 32px;
}
.kpi-item { flex: 1; padding: 0 28px; text-align: center; }
.kpi-item:first-child { padding-left: 4px; }
.kpi-divider { width: 1px; height: 48px; background: $line; flex-shrink: 0; }
.kpi-value {
    font-family: $mono;
    font-size: $s_hero;
    color: $accent;
    line-height: 1;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}
.kpi-label {
    font-family: $sans;
    font-size: $s_micro;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: $ink_2;
    margin-top: 8px;
}

/* Streamlit borde les cellules de tous les tableaux markdown, via une classe
   emotion au nom haché (`.st-emotion-cache-xxxxx th, td`) qui change à chaque
   build. Sa spécificité est de 0-2-1 ; un simple `.standings-table td` (0-1-1)
   perd. La classe est doublée ci-dessous pour atteindre 0-2-1 à notre tour :
   à spécificité égale, c'est l'ordre du document qui tranche, et notre feuille
   est injectée après la leur. Pas de `!important`, et rien qui dépende du nom
   haché — donc rien à recorriger à la prochaine version de Streamlit. */
.perf-table.perf-table th, .perf-table.perf-table td,
.league-table.league-table th, .league-table.league-table td,
.standings-table.standings-table th, .standings-table.standings-table td {
    border-left: 0;
    border-right: 0;
    border-top: 0;
    padding-left: 0;
}

/* ── Model scorecard — une ligne par ligue, l'écart à la baseline signé ── */
.perf-table { width: 100%; border-collapse: collapse; }
.perf-table thead th {
    font-family: $sans;
    font-size: $s_nano;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: $ink_3;
    padding: 0 0 10px;
    border-bottom: 1px solid $line;
    text-align: right;
    white-space: nowrap;
}
.perf-table thead th:first-child { text-align: left; }
.perf-table tbody td {
    font-family: $sans;
    font-size: $s_table;
    color: $ink;
    padding: 11px 0;
    text-align: right;
    border-bottom: 1px solid $line_2;
    white-space: nowrap;
}
.perf-table tbody td:first-child { text-align: left; }
.perf-table tbody tr:last-child td { border-bottom: none; }
.perf-table .mono {
    font-family: $mono;
    font-size: $s_num;
    color: $ink_2;
    font-variant-numeric: tabular-nums;
}
.perf-table .delta {
    font-family: $mono;
    font-size: $s_num;
    font-variant-numeric: tabular-nums;
    padding-left: 18px;
}
.perf-table .n {
    font-family: $mono;
    font-size: $s_num;
    color: $ink_2;
    font-variant-numeric: tabular-nums;
}
.better { color: $better; }
.worse  { color: $worse; }
.even   { color: $even; }

/* Barre divergente : le zéro est une position fixe, pas un bord. */
.dbar-cell { width: 168px; padding-left: 20px !important; }
.dbar {
    display: block;
    position: relative;
    height: 6px;
    background: $line_2;
    width: 160px;
    margin-left: auto;
}
.dbar::before {
    content: "";
    position: absolute;
    left: 50%;
    top: -4px;
    bottom: -4px;
    width: 1px;
    background: $ink_3;
}
.dbar i { position: absolute; top: 0; height: 6px; display: block; }

/* ── League summary ── */
.league-table { width: 100%; border-collapse: collapse; }
.league-table thead th {
    font-family: $sans;
    font-size: $s_nano;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: $ink_3;
    padding: 0 0 10px;
    border-bottom: 1px solid $line;
    text-align: right;
}
.league-table thead th:first-child { text-align: left; }
.league-table tbody tr:nth-child(even) td { background: $surface; }
.league-table tbody td {
    font-family: $sans;
    font-size: $s_table;
    color: $ink;
    padding: 10px 0;
    text-align: right;
}
.league-table tbody td:first-child { text-align: left; }
.league-table .mono {
    font-family: $mono;
    font-size: $s_num;
    color: $ink_2;
    font-variant-numeric: tabular-nums;
}

/* ── Standings table ── */
.standings-wrap { overflow-x: auto; overflow-y: auto; max-height: 680px; }
.standings-table { width: 100%; border-collapse: collapse; min-width: 620px; }
.standings-table thead tr { border-bottom: 1px solid $line; }
.standings-table thead th {
    position: sticky;
    top: 0;
    background: $ground;
    z-index: 1;
}
.standings-table th {
    font-family: $sans;
    font-size: $s_nano;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: $ink_3;
    padding: 0 16px 10px 0;
    text-align: right;
    white-space: nowrap;
}
.standings-table th.l { text-align: left; padding-right: 0; }
.standings-table td {
    padding: 8px 16px 8px 0;
    color: $ink;
    text-align: right;
    font-size: $s_table;
    border-bottom: 1px solid $line_2;
}
.standings-table td.l { text-align: left; padding-right: 0; padding-left: 8px; }
.standings-table td.rank-cell {
    font-family: $mono;
    font-size: $s_meta;
    color: $ink_3;
    text-align: left;
    padding-right: 0;
    width: 28px;
    font-variant-numeric: tabular-nums;
}
.standings-table td.rank-1 {
    font-family: $mono;
    font-size: $s_meta;
    color: $accent;
    text-align: left;
    padding-right: 0;
    width: 28px;
    font-variant-numeric: tabular-nums;
}
.standings-table td.pts {
    font-family: $mono;
    font-size: $s_table;
    color: $ink;
    font-variant-numeric: tabular-nums;
}
.standings-table td.num {
    font-family: $mono;
    font-size: $s_num;
    color: $ink_2;
    font-variant-numeric: tabular-nums;
}
.standings-table td.logo { width: 36px; }
.standings-table tbody tr:hover td { background: $surface_2; }
.standings-table tbody tr:last-child td { border-bottom: none; }
.standings-table tr.sep td { padding: 0; border: none; height: 0; }

/* ── Prediction ── */
.pred-label {
    font-family: $sans;
    font-size: $s_micro;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: $ink_2;
    display: block;
    margin-bottom: 6px;
}
.pred-vs {
    font-family: $display;
    font-style: italic;
    font-size: 1.5rem;
    color: $ink_3;
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
    font-family: $sans;
    font-size: $s_micro;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: $ink_2;
}
.prob-row-label.predicted { color: $accent; }
.prob-pct {
    font-family: $mono;
    font-size: $s_table;
    color: $ink_2;
    font-variant-numeric: tabular-nums;
}
.prob-pct.predicted { color: $ink; }
.prob-track { background: $line_2; height: 4px; }
.prob-fill { height: 4px; transition: width 0.4s ease; }
@media (prefers-reduced-motion: reduce) {
    .prob-fill { transition: none; }
}

/* ── Accuracy section ── */
.acc-row {
    display: flex;
    gap: 48px;
    margin: 20px 0;
    padding-top: 20px;
    border-top: 1px solid $line;
}
.acc-value {
    font-family: $mono;
    font-size: $s_stat;
    color: $ink;
    line-height: 1;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}
.acc-lbl {
    font-family: $sans;
    font-size: $s_micro;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: $ink_2;
    margin-top: 6px;
}
.acc-delta {
    font-family: $mono;
    font-size: $s_meta;
    margin-top: 5px;
    font-variant-numeric: tabular-nums;
}

/* ── États : vide, absent, erreur ── */
.state {
    border: 1px solid $line;
    border-left: 2px solid $accent;
    background: $surface;
    padding: 20px 22px;
    margin: 20px 0;
    max-width: 680px;
}
.state.stop { border-left-color: $worse; }
.state-title {
    font-family: $sans;
    font-size: 0.95rem;
    font-weight: 600;
    color: $ink;
    margin: 0 0 6px;
}
.state-body {
    font-family: $sans;
    font-size: $s_body;
    color: $ink_2;
    line-height: 1.65;
    margin: 0;
}
.state-body code {
    font-family: $mono;
    font-size: $s_num;
    color: $accent;
    background: $ground;
    padding: 1px 5px;
}

/* ── Sidebar — identité et repères ── */
.sb-title {
    font-family: $display;
    font-size: 1.15rem;
    font-weight: 400;
    color: $ink;
    margin: 0 0 2px;
    line-height: 1.2;
}
.sb-sub {
    font-family: $sans;
    font-size: $s_micro;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: $ink_3;
    margin: 0 0 16px;
}
.sb-rule { border-top: 1px solid $line; }
.sb-label {
    font-family: $sans;
    font-size: $s_nano;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: $ink_3;
    margin: 0 0 6px;
}
.sb-meta {
    font-family: $sans;
    font-size: 0.68rem;
    color: $ink_3;
    margin: 0;
    font-variant-numeric: tabular-nums;
}

/* ── About ── */
.about-body {
    font-family: $sans;
    font-size: $s_body;
    color: $ink_2;
    line-height: 1.7;
    max-width: 680px;
}
.about-body strong { color: $ink; font-weight: 500; }
.about-link {
    color: $accent;
    text-decoration: underline;
    text-underline-offset: 3px;
    text-decoration-color: $accent_dim;
}
.about-link:hover { text-decoration-color: $accent; }
.about-link:focus-visible { outline: 2px solid $accent; outline-offset: 2px; }
.stack-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 48px;
    margin: 16px 0;
}
.stack-row-item { padding: 8px 0; border-bottom: 1px solid $line_2; }
.stack-name { font-family: $sans; font-size: $s_table; color: $ink; }
.stack-desc { font-family: $sans; font-size: $s_num; color: $ink_3; margin-top: 1px; }

@media (max-width: 640px) {
    .kpi-row { flex-wrap: wrap; gap: 20px 0; }
    .kpi-item { flex: 1 1 44%; }
    .kpi-divider { display: none; }
    .stack-grid { grid-template-columns: 1fr; }
    .acc-row { gap: 28px; }
    .dbar-cell { display: none; }
}
</style>
"""
)


def css() -> str:
    """La feuille de style complète, construite depuis les tokens."""
    mapping = {
        "fonts_url": FONTS_URL,
        **COLOR,
        "sans": FONT["sans"],
        "mono": FONT["mono"],
        "display": FONT["display"],
        **{f"s_{k}": v for k, v in SIZE.items()},
    }
    return _CSS_TEMPLATE.substitute(mapping)


# ─────────────────────────────────────────────────────────────────────────────
# Plotly
# ─────────────────────────────────────────────────────────────────────────────


def plotly_layout(**overrides) -> dict:
    """Habillage commun des figures, dérivé des mêmes tokens.

    Aucune figure ne redéfinit ses couleurs de son côté : elle passe par ici,
    et ne choisit que ses données et sa hauteur.
    """
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR["ink_2"], family=FONT_PLOTLY["sans"], size=11),
        xaxis=dict(
            gridcolor=COLOR["line_2"],
            linecolor=COLOR["line"],
            tickcolor=COLOR["ink_3"],
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=COLOR["line_2"],
            linecolor=COLOR["line"],
            tickcolor=COLOR["ink_3"],
            zeroline=False,
        ),
        margin=dict(l=0, r=0, t=24, b=0),
        showlegend=False,
        hoverlabel=dict(
            bgcolor=COLOR["ground_2"],
            bordercolor=COLOR["line"],
            font=dict(color=COLOR["ink"], family=FONT_PLOTLY["mono"], size=11),
        ),
    )
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Helpers sémantiques
# ─────────────────────────────────────────────────────────────────────────────


def measure_class(value: float, tolerance: float = 0.0) -> str:
    """Classe CSS d'une valeur comparée à sa référence.

    C'est le seul point d'entrée des couleurs de mesure : elles ne sont jamais
    écrites en dur ailleurs.
    """
    if value > tolerance:
        return "better"
    if value < -tolerance:
        return "worse"
    return "even"


def measure_color(value: float, tolerance: float = 0.0) -> str:
    return COLOR[measure_class(value, tolerance)]


def state_block(title: str, body: str, stop: bool = False) -> str:
    """Bloc d'état (donnée absente, modèle manquant) dans la charte du dashboard."""
    cls = "state stop" if stop else "state"
    return (
        f'<div class="{cls}">'
        f'<p class="state-title">{title}</p>'
        f'<p class="state-body">{body}</p>'
        f"</div>"
    )
