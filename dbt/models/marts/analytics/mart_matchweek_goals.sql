-- Volume de buts par journée de championnat.
--
-- Remplace queries/avg_goals_per_round.sql et l'agrégation ISO-semaine que le
-- dashboard refaisait en pandas.
--
-- La journée est approximée par la semaine calendaire : les matchs d'une même
-- journée se disputent sur deux ou trois jours consécutifs. L'API expose bien
-- un champ `matchday`, mais l'ingestion Python ne le reprend pas encore dans
-- la zone curated — c'est la seule raison de cette approximation, et le jour
-- où la colonne existera ce modèle sera à reprendre (voir docs/dbt.md).

with matches as (

    select
        competition_code,
        competition_name,
        season,
        match_date,
        total_goals
    from {{ ref('stg_matches') }}
    where is_played

),

final as (

    select
        competition_code,
        competition_name,
        season,
        cast(date_trunc('week', match_date) as date) as matchweek_start,

        count(*) as matches_played,
        sum(total_goals) as goals_scored,
        max(total_goals) as max_goals_in_match,
        min(total_goals) as min_goals_in_match,
        round(cast(sum(total_goals) as double)
            / cast(count(*) as double), 3) as avg_goals_per_match

    from matches
    group by
        competition_code,
        competition_name,
        season,
        cast(date_trunc('week', match_date) as date)

)

select * from final
