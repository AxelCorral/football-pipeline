-- =============================================================================
-- top_scorers.sql
-- Top 10 équipes par nombre de buts marqués (domicile + extérieur cumulés)
--
-- Table   : matches   (base Athena définie dans ATHENA_DATABASE)
-- Période : toutes saisons confondues, matchs terminés uniquement
-- =============================================================================

SELECT
    team,
    SUM(goals_scored)                           AS total_goals_scored,
    COUNT(*)                                    AS matches_played,
    ROUND(AVG(CAST(goals_scored AS DOUBLE)), 2) AS goals_per_game
FROM (
    -- Buts à domicile
    SELECT
        home_team                   AS team,
        CAST(home_goals AS DOUBLE)  AS goals_scored
    FROM matches
    WHERE status = 'FINISHED'
      AND home_goals IS NOT NULL

    UNION ALL

    -- Buts à l'extérieur
    SELECT
        away_team                   AS team,
        CAST(away_goals AS DOUBLE)  AS goals_scored
    FROM matches
    WHERE status = 'FINISHED'
      AND away_goals IS NOT NULL
) all_goals

GROUP BY team
ORDER BY total_goals_scored DESC
LIMIT 10
