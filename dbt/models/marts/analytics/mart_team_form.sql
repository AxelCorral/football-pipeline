-- Une ligne par équipe et par saison : bilan depuis le début de saison
-- (global, domicile, extérieur) et forme la plus récente.
--
-- Deux consommateurs, deux besoins :
--   · la page Standings affiche le bilan cumulé, dans ses trois modes ;
--   · la page Prediction a besoin de la forme actuelle de n'importe quelle
--     équipe, pour composer une affiche que le calendrier ne contient pas.
--
-- Ce mart remplace compute_standings() et build_prediction_row() côté Python,
-- ainsi que queries/top_scorers.sql.
--
-- La forme reprise est celle qui suit le dernier match joué. Elle ne dit rien
-- d'un match particulier et ne peut donc pas fuiter : elle n'est valable que
-- pour une rencontre postérieure à `form_as_of`.

with team_matches as (

    select
        competition_code,
        competition_name,
        season,
        team,
        home_away,
        goals_for,
        goals_against,
        outcome,
        points,
        played_seq,
        played_seq_same_side,
        is_played
    from {{ ref('int_team_match_results') }}
    where is_played

),

season_totals as (

    select
        team,
        competition_code,
        competition_name,
        season,

        count(*) as matches_played,
        sum(case when outcome = 'WIN' then 1 else 0 end) as wins,
        sum(case when outcome = 'DRAW' then 1 else 0 end) as draws,
        sum(case when outcome = 'LOSS' then 1 else 0 end) as losses,
        sum(goals_for) as goals_for,
        sum(goals_against) as goals_against,
        sum(goals_for) - sum(goals_against) as goal_difference,
        sum(points) as points,

        sum(case when home_away = 'HOME' then 1 else 0 end) as home_matches_played,
        sum(case when home_away = 'HOME' and outcome = 'WIN' then 1 else 0 end) as home_wins,
        sum(case when home_away = 'HOME' and outcome = 'DRAW' then 1 else 0 end) as home_draws,
        sum(case when home_away = 'HOME' and outcome = 'LOSS' then 1 else 0 end) as home_losses,
        sum(case when home_away = 'HOME' then goals_for else 0 end) as home_goals_for,
        sum(case when home_away = 'HOME' then goals_against else 0 end) as home_goals_against,
        sum(case when home_away = 'HOME' then points else 0 end) as home_points,

        sum(case when home_away = 'AWAY' then 1 else 0 end) as away_matches_played,
        sum(case when home_away = 'AWAY' and outcome = 'WIN' then 1 else 0 end) as away_wins,
        sum(case when home_away = 'AWAY' and outcome = 'DRAW' then 1 else 0 end) as away_draws,
        sum(case when home_away = 'AWAY' and outcome = 'LOSS' then 1 else 0 end) as away_losses,
        sum(case when home_away = 'AWAY' then goals_for else 0 end) as away_goals_for,
        sum(case when home_away = 'AWAY' then goals_against else 0 end) as away_goals_against,
        sum(case when home_away = 'AWAY' then points else 0 end) as away_points,

        max(played_seq) as last_played_seq,
        max(case when home_away = 'HOME' then played_seq_same_side end) as last_home_seq,
        max(case when home_away = 'AWAY' then played_seq_same_side end) as last_away_seq

    from team_matches
    group by team, competition_code, competition_name, season

),

overall_form as (
    select * from {{ ref('int_team_form') }}
),

side_form as (
    select * from {{ ref('int_home_away_form') }}
),

final as (

    select
        s.team,
        s.competition_code,
        s.competition_name,
        s.season,

        s.matches_played,
        s.wins,
        s.draws,
        s.losses,
        s.goals_for,
        s.goals_against,
        s.goal_difference,
        s.points,

        s.home_matches_played,
        s.home_wins,
        s.home_draws,
        s.home_losses,
        s.home_goals_for,
        s.home_goals_against,
        s.home_goals_for - s.home_goals_against as home_goal_difference,
        s.home_points,

        s.away_matches_played,
        s.away_wins,
        s.away_draws,
        s.away_losses,
        s.away_goals_for,
        s.away_goals_against,
        s.away_goals_for - s.away_goals_against as away_goal_difference,
        s.away_points,

        -- Forme récente, toutes rencontres confondues
        f.form_as_of,
        f.matches_in_window as form_matches,
        f.form_points,
        f.form_wins,
        f.form_draws,
        f.form_losses,
        f.form_goal_difference,
        f.form_avg_points,
        f.form_avg_goals_for,
        f.form_avg_goals_against,

        -- Forme récente à domicile / à l'extérieur : ce sont ces colonnes que
        -- la page Prediction assemble pour une affiche arbitraire.
        hf.form_as_of as home_form_as_of,
        hf.matches_in_window as home_form_matches,
        hf.form_avg_points as home_form_avg_points,
        hf.form_avg_goals_for as home_form_avg_goals_for,
        hf.form_avg_goals_against as home_form_avg_goals_against,

        af.form_as_of as away_form_as_of,
        af.matches_in_window as away_form_matches,
        af.form_avg_points as away_form_avg_points,
        af.form_avg_goals_for as away_form_avg_goals_for,
        af.form_avg_goals_against as away_form_avg_goals_against

    from season_totals as s

    left join overall_form as f
        on f.team = s.team
        and f.competition_code = s.competition_code
        and f.season = s.season
        and f.played_seq = s.last_played_seq

    left join side_form as hf
        on hf.team = s.team
        and hf.competition_code = s.competition_code
        and hf.season = s.season
        and hf.home_away = 'HOME'
        and hf.played_seq_same_side = s.last_home_seq

    left join side_form as af
        on af.team = s.team
        and af.competition_code = s.competition_code
        and af.season = s.season
        and af.home_away = 'AWAY'
        and af.played_seq_same_side = s.last_away_seq

)

select * from final
