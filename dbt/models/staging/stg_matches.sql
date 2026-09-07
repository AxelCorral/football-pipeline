-- Représentation propre et stable d'un match : une ligne par match_id.
--
-- Trois choses seulement se passent ici — typage/renommage, filtrage des
-- lignes inexploitables, déduplication. Aucune règle métier, aucune
-- agrégation : elles appartiennent à la couche intermediate.

with source as (

    select
        match_id,
        "date",
        competition,
        competition_code,
        season,
        home_team,
        away_team,
        home_goals,
        away_goals,
        status,
        referee
    -- `venue` n'est pas repris : la colonne est présente dans la zone curated
    -- mais vide sur 100 % des lignes (l'API ne la renseigne pas pour ces
    -- compétitions). La reprendre reviendrait à documenter du vide.
    from {{ source('football_curated', 'matches') }}

),

typed as (

    select
        cast(match_id as bigint) as match_id,
        cast("date" as timestamp) as match_date,
        upper(trim(cast(competition_code as varchar))) as competition_code,
        trim(cast(competition as varchar)) as competition_name,
        cast(season as integer) as season,
        trim(cast(home_team as varchar)) as home_team,
        trim(cast(away_team as varchar)) as away_team,
        cast(home_goals as integer) as home_goals,
        cast(away_goals as integer) as away_goals,
        upper(trim(cast(status as varchar))) as status,
        nullif(trim(cast(referee as varchar)), '') as referee
    from source

),

valid as (

    -- Une ligne sans identifiant, sans date ou opposant une équipe à
    -- elle-même n'est pas un match : elle est écartée plutôt que propagée.
    select *
    from typed
    where match_id is not null
      and match_date is not null
      and home_team is not null
      and away_team is not null
      and home_team <> away_team

),

deduplicated as (

    -- La zone curated est réécrite en relisant l'intégralité de raw/ : rejouer
    -- l'ingestion sur les mêmes partitions y laisse des copies du même match
    -- (760 lignes pour 380 matchs de Premier League au moment de l'écriture).
    -- On garde la version la plus avancée du match — jouée avant programmée,
    -- puis la plus récente.
    select
        *,
        row_number() over (
            partition by match_id
            order by
                case when status in ('FINISHED', 'AWARDED') then 0 else 1 end,
                match_date desc
        ) as row_num
    from valid

),

final as (

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

        case
            when home_goals is not null and away_goals is not null
                then home_goals + away_goals
        end as total_goals,

        status,

        -- AWARDED = match attribué sur tapis vert : il a un score définitif et
        -- compte donc comme joué, au même titre que FINISHED.
        (status in ('FINISHED', 'AWARDED')
            and home_goals is not null
            and away_goals is not null) as is_played,

        -- Recalculé plutôt que repris de la source : une seule règle H/D/A
        -- dans tout le projet, et elle est ici.
        case
            when home_goals is null or away_goals is null then null
            when home_goals > away_goals then 'H'
            when home_goals < away_goals then 'A'
            else 'D'
        end as result,

        referee

    from deduplicated
    where row_num = 1

)

select * from final
