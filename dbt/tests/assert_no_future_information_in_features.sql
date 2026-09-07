-- Le test de fuite temporelle central.
--
-- Il ne fait pas confiance aux colonnes form_as_of : il recalcule, à partir de
-- l'historique brut, ce que chaque fenêtre de forme aurait dû contenir, et
-- vérifie que les features publiées correspondent.
--
-- Concrètement, pour chaque match du mart et chaque équipe, on reconstruit la
-- moyenne de points sur les 5 derniers matchs joués STRICTEMENT avant le coup
-- d'envoi — par une jointure sur les dates, sans fenêtre glissante, donc par un
-- chemin de calcul indépendant de celui du mart. Toute différence signale soit
-- une fuite (le match courant ou un match postérieur est entré dans la
-- fenêtre), soit une erreur de rattachement.

with features as (

    select
        match_id,
        match_date,
        competition_code,
        season,
        home_team,
        home_home_avg_points_last_5,
        away_team,
        away_away_avg_points_last_5
    from {{ ref('fct_match_features') }}

),

history as (

    select
        match_date,
        competition_code,
        season,
        team,
        home_away,
        points
    from {{ ref('int_team_match_results') }}
    where is_played

),

-- Un couple (match, équipe) par côté, pour traiter domicile et extérieur
-- avec la même requête.
sides as (

    select
        match_id, match_date, competition_code, season,
        home_team as team, 'HOME' as home_away,
        home_home_avg_points_last_5 as published_avg_points
    from features

    union all

    select
        match_id, match_date, competition_code, season,
        away_team as team, 'AWAY' as home_away,
        away_away_avg_points_last_5 as published_avg_points
    from features

),

-- Les matchs antérieurs de l'équipe, du même côté, numérotés du plus récent au
-- plus ancien. Le rattachement se fait sur les dates seules : aucune fenêtre,
-- aucun rang précalculé, aucun emprunt à la logique testée.
ranked_history as (

    select
        s.match_id,
        s.team,
        s.home_away,
        s.published_avg_points,
        h.points,
        row_number() over (
            partition by s.match_id, s.team, s.home_away
            order by h.match_date desc
        ) as recency
    from sides as s
    inner join history as h
        on h.team = s.team
        and h.competition_code = s.competition_code
        and h.season = s.season
        and h.home_away = s.home_away
        and h.match_date < s.match_date

),

recomputed as (

    select
        match_id,
        team,
        home_away,
        max(published_avg_points) as published_avg_points,
        cast(sum(points) as double) / cast(count(*) as double) as expected_avg_points
    from ranked_history
    where recency <= {{ var('form_window') }}
    group by match_id, team, home_away

)

select *
from recomputed
where published_avg_points is null
   or abs(published_avg_points - expected_avg_points) > 1e-9
