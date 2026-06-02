-- =============================================================================
-- home_advantage.sql
-- Avantage du terrain par compétition :
--   % victoires à domicile / à l'extérieur / nul
--
-- Table   : matches   (base Athena définie dans ATHENA_DATABASE)
-- Résultat : 1 ligne par compétition, triée par home_win_pct décroissant
-- Colonne result : 'H' = victoire domicile, 'A' = victoire extérieur,
--                  'D' = match nul, NULL = match non terminé (exclu)
-- =============================================================================

SELECT
    competition,
    COUNT(*)                                                             AS total_matches,

    SUM(CASE WHEN result = 'H' THEN 1 ELSE 0 END)                       AS home_wins,
    SUM(CASE WHEN result = 'A' THEN 1 ELSE 0 END)                       AS away_wins,
    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END)                       AS draws,

    ROUND(
        100.0 * SUM(CASE WHEN result = 'H' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    )                                                                    AS home_win_pct,

    ROUND(
        100.0 * SUM(CASE WHEN result = 'A' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    )                                                                    AS away_win_pct,

    ROUND(
        100.0 * SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    )                                                                    AS draw_pct

FROM matches
WHERE status  = 'FINISHED'
  AND result IS NOT NULL

GROUP BY competition
ORDER BY home_win_pct DESC
