-- Symétrique du test « pas d'historique ⇒ features NULL ».
--
-- Une jointure de forme cassée — mauvaise clé, saison décalée, rang décalé de
-- un — ne lèverait aucune erreur : elle produirait simplement des features
-- NULL partout, et le pipeline ML entraînerait sur un dataset vide sans que
-- rien ne le signale. Ce test rend cette panne bruyante : dès qu'une équipe a
-- au moins un match joué derrière elle, ses features doivent exister.

select
    match_id,
    match_date,
    competition_code,
    home_team,
    away_team,
    home_matches_played,
    away_matches_played,
    home_home_matches_played,
    away_away_matches_played,
    home_avg_points_last_5,
    away_avg_points_last_5,
    home_home_avg_points_last_5,
    away_away_avg_points_last_5
from {{ ref('fct_match_features') }}
where (home_matches_played > 0 and home_avg_points_last_5 is null)
   or (away_matches_played > 0 and away_avg_points_last_5 is null)
   or (home_home_matches_played > 0 and home_home_avg_points_last_5 is null)
   or (away_away_matches_played > 0 and away_away_avg_points_last_5 is null)
