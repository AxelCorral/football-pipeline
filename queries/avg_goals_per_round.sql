-- =============================================================================
-- avg_goals_per_round.sql
-- Moyenne de buts par journée de championnat, par compétition et saison
--
-- Table   : matches   (base Athena définie dans ATHENA_DATABASE)
-- Journée : semaine calendaire (DATE_TRUNC 'week') — proxy fidèle des
--           journées de championnat (les matchs d'une même journée se
--           jouent généralement sur 2-3 jours consécutifs).
--           Pour une précision exacte, ajouter la colonne `matchday` au
--           pipeline de transformation (src/transform/process_matches.py).
-- =============================================================================

SELECT
    competition,
    CAST(season AS VARCHAR)                              AS season,
    DATE_TRUNC('week', "date")                          AS round_week,

    COUNT(*)                                             AS matches_in_round,
    SUM(CAST(total_goals AS BIGINT))                     AS goals_in_round,
    ROUND(AVG(CAST(total_goals AS DOUBLE)), 2)           AS avg_goals_per_match,

    -- Extremes utiles pour détecter les journées prolifiques / stériles
    MAX(CAST(total_goals AS BIGINT))                     AS max_goals_in_match,
    MIN(CAST(total_goals AS BIGINT))                     AS min_goals_in_match

FROM matches
WHERE status      = 'FINISHED'
  AND total_goals IS NOT NULL

GROUP BY
    competition,
    season,
    DATE_TRUNC('week', "date")

ORDER BY
    competition,
    season,
    round_week
