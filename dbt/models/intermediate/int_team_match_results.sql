-- Passage du grain « match » au grain « équipe × match ».
--
--   match 100 : PSG 3 - 1 Lyon
--   →  PSG  | Lyon | HOME | 3 | 1 | WIN  | 3 pts
--      Lyon | PSG  | AWAY | 1 | 3 | LOSS | 0 pt
--
-- C'est la forme sous laquelle un historique d'équipe se calcule sans avoir à
-- traiter séparément les colonnes domicile et extérieur.
--
-- Le modèle porte aussi les compteurs de chronologie utilisés en aval :
-- `prior_played_matches` et `prior_played_matches_same_side` comptent les
-- matchs JOUÉS strictement avant la ligne courante. Ce sont eux qui rendent la
-- construction des features insensible aux matchs reportés et aux matchs à
-- venir intercalés dans le calendrier.

with matches as (

    select
        match_id,
        match_date,
        competition_code,
        competition_name,
        season,
        home_team,
        away_team,
        home_goals,
        away_goals,
        is_played,
        result
    from {{ ref('stg_matches') }}

),

team_matches as (

    select
        match_id,
        match_date,
        competition_code,
        competition_name,
        season,
        home_team as team,
        away_team as opponent,
        'HOME' as home_away,
        home_goals as goals_for,
        away_goals as goals_against,
        is_played,
        case
            when result = 'H' then 'WIN'
            when result = 'A' then 'LOSS'
            when result = 'D' then 'DRAW'
        end as outcome,
        case
            when result = 'H' then 3
            when result = 'D' then 1
            when result = 'A' then 0
        end as points
    from matches

    union all

    select
        match_id,
        match_date,
        competition_code,
        competition_name,
        season,
        away_team as team,
        home_team as opponent,
        'AWAY' as home_away,
        away_goals as goals_for,
        home_goals as goals_against,
        is_played,
        case
            when result = 'A' then 'WIN'
            when result = 'H' then 'LOSS'
            when result = 'D' then 'DRAW'
        end as outcome,
        case
            when result = 'A' then 3
            when result = 'D' then 1
            when result = 'H' then 0
        end as points
    from matches

),

sequenced as (

    select
        *,

        -- Rang du match dans l'historique joué de l'équipe. NULL pour un match
        -- sans score : partitionner sur is_played numérote les matchs joués
        -- entre eux, indépendamment des matchs programmés ou reportés.
        case when is_played then
            row_number() over (
                partition by team, competition_code, season, is_played
                order by match_date, match_id
            )
        end as played_seq,

        case when is_played then
            row_number() over (
                partition by team, competition_code, season, home_away, is_played
                order by match_date, match_id
            )
        end as played_seq_same_side,

        -- Nombre de matchs joués strictement avant celui-ci. Défini pour TOUTE
        -- ligne, jouée ou non : c'est la clé qui permet d'attacher une forme
        -- d'avant-match aussi bien à un match passé qu'à une rencontre à venir.
        coalesce(sum(case when is_played then 1 else 0 end) over (
            partition by team, competition_code, season
            order by match_date, match_id
            rows between unbounded preceding and 1 preceding
        ), 0) as prior_played_matches,

        coalesce(sum(case when is_played then 1 else 0 end) over (
            partition by team, competition_code, season, home_away
            order by match_date, match_id
            rows between unbounded preceding and 1 preceding
        ), 0) as prior_played_matches_same_side

    from team_matches

),

final as (

    select
        match_id,
        match_date,
        competition_code,
        competition_name,
        season,
        team,
        opponent,
        home_away,
        goals_for,
        goals_against,
        case
            when goals_for is not null and goals_against is not null
                then goals_for - goals_against
        end as goal_difference,
        is_played,
        outcome,
        points,
        played_seq,
        played_seq_same_side,
        prior_played_matches,
        prior_played_matches_same_side
    from sequenced

)

select * from final
