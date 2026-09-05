# Système de design — Football Pipeline

**Ce document fait autorité.** En cas de contradiction avec une décision
graphique antérieure ou avec ce que fait le code, c'est ce document qui
l'emporte, et le code qui se corrige.

Implémentation : `src/ui/theme.py` pour tout ce que Streamlit ne sait pas
faire nativement, `.streamlit/config.toml` pour le reste. **Aucune valeur de
couleur, de police ou de taille n'est écrite ailleurs.**

> Le parti pris tient en une phrase : **une page de résultats sportifs, pas un
> tableau de bord d'entreprise.** Un titre en serif, des chiffres en chasse
> fixe, des filets plutôt que des cartes, et de l'or utilisé avec parcimonie.

---

## Couleurs

Trois familles. Elles ne se mélangent jamais, et c'est la règle la plus
importante de ce document.

### Structure — neutres

| Token | Hex | Rôle |
|---|---|---|
| `ground` | `#111111` | fond de page |
| `ground_2` | `#0D0D0D` | sidebar, fond de survol d'info-bulle |
| `surface` | `#141414` | ligne alternée de tableau |
| `surface_2` | `#161616` | survol de ligne |
| `line` | `#2E2E2E` | filet structurant : sections, en-têtes, bordures |
| `line_2` | `#1A1A1A` | filet interne de tableau, piste de barre |
| `ink` | `#F5F5F5` | texte principal, chiffre mis en avant |
| `ink_2` | `#888888` | texte secondaire, étiquette de section |
| `ink_3` | `#555555` | étiquette de colonne, texte tertiaire, série en retrait |

### Marque — l'or

| Token | Hex | Rôle |
|---|---|---|
| `accent` | `#C8A96E` | identité, état actif, valeur mise en avant |
| `accent_dim` | `rgba(200,169,110,.4)` | soulignement de lien au repos |

**Règle : une seule utilisation emphatique de l'or par vue.** Dans une figure,
l'or désigne un et un seul élément — la meilleure attaque, l'issue prédite.
Si deux choses sont en or dans la même vue, aucune ne ressort.

### Mesure — sémantiques

| Token | Hex | Rôle |
|---|---|---|
| `better` | `#4CAF7D` | valeur au-dessus de sa référence |
| `worse` | `#E05C5C` | valeur en dessous de sa référence |
| `even` | `#888888` | égale, ou pas de référence |

**Règle absolue.** Ces trois couleurs ne qualifient qu'**une valeur comparée à
une référence explicite et nommée** — aujourd'hui, l'accuracy face à la
baseline naïve. Elles ne sont jamais une couleur de marque, jamais un fond de
bouton, jamais un décor, et **jamais une série de graphique choisie par
commodité**. Trois issues de match ne sont ni bonnes ni mauvaises : elles ne
prennent pas ces couleurs.

Seul point d'entrée : `theme.measure_class()` et `theme.measure_color()`.
Écrire `#4CAF7D` à la main dans un fichier est un bug.

---

## Typographie

| Famille | Emploi |
|---|---|
| **DM Serif Display** 400 | titres de page (`h1`), le « vs » de la page Prediction. Rien d'autre. |
| **DM Sans** 300–600 | tout le texte courant, étiquettes, en-têtes de tableau |
| **DM Mono** 300–500 | **tout chiffre destiné à être comparé** : KPI, colonnes de tableau, pourcentages, écarts |

La règle sur DM Mono n'est pas décorative : un chiffre qu'on lit en colonne
doit s'aligner. Tout élément qui affiche des nombres alignés porte
`font-variant-numeric: tabular-nums`.

### Échelle

| Token | Taille | Emploi |
|---|---|---|
| `hero` | 2.8rem | chiffre de KPI |
| `stat` | 2.4rem | chiffre de mesure (accuracy, baseline) |
| `h1` | 2.2rem | titre de page |
| `body` | 0.9rem | texte courant |
| `table` | 0.88rem | cellule de tableau |
| `num` | 0.82rem | chiffre secondaire en tableau |
| `meta` | 0.78rem | écart, mention |
| `label` | 0.7rem | étiquette de section (`.sl`) |
| `micro` | 0.65rem | étiquette de KPI |
| `nano` | 0.62rem | en-tête de colonne |

Les étiquettes en capitales portent un interlettrage de `0.12em` à `0.15em`.
Sans lui, une capitale de 0,62 rem est illisible.

## Espacement

Une seule graduation, en pixels : **4 · 8 · 12 · 16 · 20 · 28 · 40 · 56.**
Une valeur hors de cette liste est une erreur, pas une exception.

---

## Interdits

1. **Pas d'angle arrondi.** `baseRadius` et `buttonRadius` sont à `none`. La
   charte est éditoriale : les arêtes sont vives.
2. **Pas d'ombre portée**, nulle part. La profondeur vient des filets.
3. **Pas de carte.** Les sections sont séparées par un filet supérieur et une
   étiquette (`.sl`), pas par un rectangle bordé. Seule exception : le bloc
   d'état (`.state`), parce qu'il doit interrompre la lecture.
4. **Pas de dégradé**, ni en fond, ni dans une figure.
5. **Pas d'emoji comme élément d'interface.** Les drapeaux de compétition de
   `COMPETITION_FLAGS` sont tolérés comme donnée héritée ; n'en ajoute pas.
6. **Pas d'animation décorative.** La seule transition du projet est le
   remplissage des barres de probabilité, qui montre un changement d'état, et
   elle est désactivée sous `prefers-reduced-motion`.
7. **Pas de couleur de mesure sur une série de graphique** qui ne compare rien
   à une référence.

---

## Où chaque chose est définie

| Catégorie | Adresse unique |
|---|---|
| Couleurs, polices, échelles | `src/ui/theme.py` → `COLOR`, `FONT`, `SIZE`, `SPACE` |
| Feuille de style | `src/ui/theme.py` → `css()` |
| Habillage des figures Plotly | `src/ui/theme.py` → `plotly_layout()` |
| Couleur de mesure | `src/ui/theme.py` → `measure_class()` / `measure_color()` |
| Bloc d'état | `src/ui/theme.py` → `state_block()` |
| Thème natif Streamlit | `.streamlit/config.toml` |

**Priorité : le thème natif d'abord.** Tout ce que `config.toml` sait déclarer
s'y déclare, et ne s'écrit pas en CSS. Un `!important` sur un sélecteur
`data-testid` est interne à Streamlit et casse à la montée de version ; une clé
de thème, non. Le CSS injecté ne sert qu'à ce que le thème natif ne couvre pas.

## Règles de contribution

- Une figure ne choisit que ses **données** et sa **hauteur**. Son habillage
  vient de `plotly_layout()`. Aucune figure ne définit ses couleurs de son côté.
- Un tableau de données affiché à l'utilisateur passe par du HTML au thème, pas
  par `st.dataframe` : sa grille ignore le thème. Le prix à payer est la perte
  du tri interactif — acceptable ici, où l'ordre du classement est le seul qui
  compte. Le jour où un tri utilisateur devient nécessaire, c'est ce document
  qu'il faut rouvrir, pas une exception qu'il faut glisser dans le code.
- Un état vide, absent ou en erreur passe par `state_block()`, jamais par
  `st.error` / `st.warning`, qui apportent leur propre palette.
