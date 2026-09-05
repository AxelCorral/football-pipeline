# Audit UI — état avant la passe

Constaté par lecture de `app.py` (1 204 lignes) et de `.streamlit/config.toml`,
le 5 septembre 2026. Un défaut par ligne, avec sa raison.

## Système

| # | Défaut | Pourquoi c'en est un |
|---|---|---|
| 1 | Aucune source de tokens. `#2E2E2E`, `#C8A96E`, `'DM Sans'` apparaissent dans les 375 lignes de CSS injecté **et** dans des f-strings HTML en Python. | Changer une couleur demande un rechercher-remplacer dans deux langages. Rien ne garantit qu'on les attrape toutes. |
| 2 | Deux systèmes de couleur se contredisent. `#4CAF7D` / `#E05C5C` signifient « victoire domicile / extérieur » sur Prediction, et « au-dessus / en dessous de la baseline » sur le bloc d'accuracy — sur la même page. | Le vert et le rouge disent « bien / mal ». Une victoire à l'extérieur n'est pas un mauvais résultat, et le lecteur apprend deux grammaires contradictoires en une vue. |
| 3 | 6 clés de thème natif utilisées sur ~90 disponibles en Streamlit 1.58. Tout le reste est forcé en `!important` sur des sélecteurs `data-testid`. | Ces sélecteurs sont internes à Streamlit et changent entre versions. Chaque override est une casse programmée. |

## Overview

| # | Défaut | Pourquoi c'en est un |
|---|---|---|
| 4 | L'écart du modèle à la baseline n'existe que sur la page Prediction, après un clic, et pour une seule ligue à la fois. | C'est la chose la plus distinctive du projet — publier les ligues où le modèle perd. Un visiteur ne voit jamais la Serie A à +9,7 pts et la Bundesliga à −0,7 côte à côte. Le point du projet est invisible. |
| 5 | Courbe hebdomadaire : étiquettes `2025-W36` inclinées à −45°, sur une quarantaine de semaines. | Illisible, et l'inclinaison mange de la hauteur utile pour rien. |

## Standings

| # | Défaut | Pourquoi c'en est un |
|---|---|---|
| 6 | `_standings_html()` — 60 lignes qui produisent un tableau à la typographie du projet, avec écussons et premier rang en or — **n'est jamais appelée**. La page rend `st.dataframe`. | La grille de `st.dataframe` ignore le thème : sa police, ses bordures et son en-tête lui appartiennent. C'est le seul écran qui ressemble à du Streamlit par défaut, et le bon tableau était déjà écrit. |

## Prediction

| # | Défaut | Pourquoi c'en est un |
|---|---|---|
| 7 | Les trois issues sont vert / gris / rouge. | Voir 2. Une seule des trois est prédite : c'est *ça* que la couleur doit dire. |
| 8 | Les trois pourcentages ont la même couleur. L'étiquette de l'issue prédite passe en or, mais pas son chiffre. | L'œil va au chiffre, pas à l'étiquette. L'emphase est mise à l'endroit qu'on ne lit pas. |

## Tous les écrans

| # | Défaut | Pourquoi c'en est un |
|---|---|---|
| 9 | États vides et erreurs en `st.error` / `st.warning` bruts. | Encadrés rouges et orange de la palette Streamlit, avec icône : c'est ce qui trahit le plus vite un prototype, et ces états sont exactement ceux qu'un visiteur rencontre quand quelque chose manque. |
| 10 | Aucun style de focus clavier sur le bouton primaire. | Le bouton est le seul élément d'action de l'app. Il est inatteignable visuellement au clavier. |

## Ce qui va bien — à ne pas casser

- La direction « Editorial Sports » est cohérente et assumée : DM Serif Display,
  DM Sans, DM Mono, fond `#111111`, or `#C8A96E`.
- La navigation sidebar en radio restylée (filet à gauche sur l'entrée active)
  est meilleure que tout ce que Streamlit propose nativement.
- `_PLOTLY` existait déjà : les figures n'étaient **pas** au thème Plotly par
  défaut, contrairement à ce que supposait le prompt de cette passe. Fond
  transparent, DM Sans, grille sombre — la base était bonne.
