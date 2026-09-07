-- KPI d'un championnat sur une saison : volumétrie, buts, avantage du terrain.
--
-- Remplace queries/home_advantage.sql et les agrégats que le dashboard
-- recalculait à chaque affichage de la page Overview.

with team_matches as (

    select
        match_id,
        competition_code,
        competition_name,
        season,
        team,
        goals_for,
        is_played
    from {{ ref('int_team_match_results') }}

),

matches as (

    select
        competition_code,
        competition_name,
        season,
        match_id,
        result,
        total_goals,
        match_date
    from {{ ref('stg_matches') }}
    where is_played

),

match_level as (

    select
        competition_code,
        competition_name,
        season,

        count(*) as matches_played,
        sum(total_goals) as goals_scored,
        sum(case when result = 'H' then 1 else 0 end) as home_wins,
        sum(case when result = 'D' then 1 else 0 end) as draws,
        sum(case when result = 'A' then 1 else 0 end) as away_wins,
        min(match_date) as first_match_date,
        max(match_date) as last_match_date

    from matches
    group by competition_code, competition_name, season

),

team_level as (

    select
        competition_code,
        season,
        count(distinct team) as teams
    from team_matches
    group by competition_code, season

),

final as (

    select
        m.competition_code,
        m.competition_name,
        m.season,
        t.teams,
        m.matches_played,
        m.goals_scored,
        m.home_wins,
        m.draws,
        m.away_wins,
        m.first_match_date,
        m.last_match_date,

        round(cast(m.goals_scored as double)
            / cast(m.matches_played as double), 3) as avg_goals_per_match,
        round(100.0 * cast(m.home_wins as double)
            / cast(m.matches_played as double), 2) as home_win_pct,
        round(100.0 * cast(m.draws as double)
            / cast(m.matches_played as double), 2) as draw_pct,
        round(100.0 * cast(m.away_wins as double)
            / cast(m.matches_played as double), 2) as away_win_pct

    from match_level as m
    inner join team_level as t
        on t.competition_code = m.competition_code
        and t.season = m.season

)

select * from final
