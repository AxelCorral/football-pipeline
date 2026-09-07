-- Forme d'une équipe, toutes rencontres confondues, sur les
-- `form_window` derniers matchs joués.
--
-- Une ligne = l'état d'une équipe APRÈS son n-ième match joué de la saison
-- (`played_seq`). La fenêtre inclut donc le match n : ce modèle décrit un état
-- atteint, pas une prédiction. C'est en aval, dans fct_match_features, que la
-- ligne n est rattachée au match n+1 — jamais au match n lui-même.
--
-- `form_as_of` porte cette sémantique dans les données : c'est la date du
-- dernier match compté dans la fenêtre. Tout consommateur peut vérifier que
-- form_as_of est strictement antérieur au match qu'il décrit.

with played as (

    select
        match_id,
        match_date,
        competition_code,
        season,
        team,
        played_seq,
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
        played_seq,
        match_date as form_as_of,

        count(*) {{ form_frame('team, competition_code, season') }}
            as matches_in_window,
        sum(points) {{ form_frame('team, competition_code, season') }}
            as points_in_window,
        sum(case when outcome = 'WIN' then 1 else 0 end)
            {{ form_frame('team, competition_code, season') }} as wins_in_window,
        sum(case when outcome = 'DRAW' then 1 else 0 end)
            {{ form_frame('team, competition_code, season') }} as draws_in_window,
        sum(case when outcome = 'LOSS' then 1 else 0 end)
            {{ form_frame('team, competition_code, season') }} as losses_in_window,
        sum(goals_for) {{ form_frame('team, competition_code, season') }}
            as goals_for_in_window,
        sum(goals_against) {{ form_frame('team, competition_code, season') }}
            as goals_against_in_window

    from played

),

final as (

    select
        team,
        competition_code,
        season,
        played_seq,
        form_as_of,
        matches_in_window,
        points_in_window as form_points,
        wins_in_window as form_wins,
        draws_in_window as form_draws,
        losses_in_window as form_losses,
        goals_for_in_window as form_goals_for,
        goals_against_in_window as form_goals_against,
        goals_for_in_window - goals_against_in_window as form_goal_difference,

        -- CAST explicite avant chaque division : sur Athena (Trino) la division
        -- de deux entiers est entière, sur DuckDB elle ne l'est pas. Sans le
        -- cast, la même requête donnerait deux résultats selon la cible.
        cast(points_in_window as double)
            / cast(matches_in_window as double) as form_avg_points,
        cast(goals_for_in_window as double)
            / cast(matches_in_window as double) as form_avg_goals_for,
        cast(goals_against_in_window as double)
            / cast(matches_in_window as double) as form_avg_goals_against

    from windowed

)

select * from final
