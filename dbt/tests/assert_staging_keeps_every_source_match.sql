-- La déduplication de stg_matches supprime des lignes ; elle ne doit jamais
-- supprimer de match.
--
-- Le test compare le nombre de match_id distincts et exploitables de la source
-- au nombre de lignes de stg_matches. Un écart signifie que le row_number()
-- a écarté plus que des copies, ou que le filtrage `valid` est devenu trop
-- large.

with source_matches as (

    select count(distinct match_id) as n
    from {{ source('football_curated', 'matches') }}
    where match_id is not null
      and "date" is not null
      and home_team is not null
      and away_team is not null
      and trim(cast(home_team as varchar)) <> trim(cast(away_team as varchar))

),

staged_matches as (

    select count(*) as n
    from {{ ref('stg_matches') }}

)

select
    source_matches.n as source_match_count,
    staged_matches.n as staged_match_count
from source_matches
cross join staged_matches
where source_matches.n <> staged_matches.n
