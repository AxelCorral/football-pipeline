-- Forme d'une équipe restreinte à un seul contexte : ses matchs à domicile
-- d'un côté, ses matchs à l'extérieur de l'autre.
--
-- Même sémantique que int_team_form — une ligne est l'état APRÈS le n-ième
-- match joué dans ce contexte (`played_seq_same_side`) — mais la fenêtre ne
-- voit que les matchs du même côté. C'est cette version, et non la forme
-- globale, qui alimente les features du modèle : « ce que Lyon fait à
-- l'extérieur » explique mieux un déplacement à Lyon que sa forme générale.

with played as (

    select
        match_id,
        match_date,
        competition_code,
        season,
        team,
        home_away,
        played_seq_same_side,
        goals_for,
        goals_against,
        outcome,
        points
    from {{ ref('int_team_match_results') }}
    where is_played

),

windowed as (

    select
        team,
        competition_code,
        season,
        home_away,
        played_seq_same_side,
        match_date as form_as_of,

        count(*) {{ form_frame('team, competition_code, season, home_away') }}
            as matches_in_window,
        sum(points) {{ form_frame('team, competition_code, season, home_away') }}
            as points_in_window,
        sum(case when outcome = 'WIN' then 1 else 0 end)
            {{ form_frame('team, competition_code, season, home_away') }} as wins_in_window,
        sum(case when outcome = 'DRAW' then 1 else 0 end)
            {{ form_frame('team, competition_code, season, home_away') }} as draws_in_window,
        sum(case when outcome = 'LOSS' then 1 else 0 end)
            {{ form_frame('team, competition_code, season, home_away') }} as losses_in_window,
        sum(goals_for) {{ form_frame('team, competition_code, season, home_away') }}
            as goals_for_in_window,
        sum(goals_against) {{ form_frame('team, competition_code, season, home_away') }}
            as goals_against_in_window

    from played

),

final as (

    select
        team,
        competition_code,
        season,
        home_away,
        played_seq_same_side,
        form_as_of,
        matches_in_window,
        points_in_window as form_points,
        wins_in_window as form_wins,
        draws_in_window as form_draws,
        losses_in_window as form_losses,
        goals_for_in_window as form_goals_for,
        goals_against_in_window as form_goals_against,
        goals_for_in_window - goals_against_in_window as form_goal_difference,

        cast(points_in_window as double)
            / cast(matches_in_window as double) as form_avg_points,
        cast(goals_for_in_window as double)
            / cast(matches_in_window as double) as form_avg_goals_for,
        cast(goals_against_in_window as double)
            / cast(matches_in_window as double) as form_avg_goals_against

    from windowed

)

select * from final
