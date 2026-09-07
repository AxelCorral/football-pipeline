-- Dataset de features : une ligne par match, prête à être chargée telle quelle
-- par le pipeline ML Python.
--
-- ── Absence de fuite temporelle ──────────────────────────────────────────────
--
-- Toute la garantie tient dans une jointure. Pour le match M d'une équipe :
--
--     forme retenue = ligne de int_team_form dont le rang (played_seq) vaut le
--                     nombre de matchs joués strictement AVANT M
--                     (prior_played_matches, calculé dans
--                     int_team_match_results sur `rows between unbounded
--                     preceding and 1 preceding`)
--
-- Le match M n'est donc jamais dans sa propre fenêtre, et aucun match
-- postérieur ne peut y entrer puisque les rangs suivent l'ordre chronologique
-- (match_date, match_id).
--
-- Le passage par un rang plutôt que par une fenêtre `N preceding and 1
-- preceding` posée directement sur le match est délibéré : il rend le calcul
-- exact quand des matchs non joués (reportés, à venir) s'intercalent dans le
-- calendrier d'une équipe. Une fenêtre par lignes compterait ces matchs sans
-- score comme de l'historique ; le rang, lui, ne compte que du joué.
--
-- `home_form_as_of` / `away_form_as_of` exposent la date du dernier match
-- entré dans chaque fenêtre : le test singulier
-- assert_no_future_information_in_features vérifie qu'elle est strictement
-- antérieure au coup d'envoi.
--
-- ── Historique insuffisant ──────────────────────────────────────────────────
--
-- Une équipe sans match joué avant M (première journée, promu) n'a pas de
-- ligne de forme correspondante : les LEFT JOIN laissent les features à NULL,
-- et *_matches_played vaut 0. Rien n'est imputé à zéro — un zéro se
-- confondrait avec « a joué et n'a pris aucun point ». Le tri des lignes
-- exploitables appartient au consommateur.

with matches as (

    select
        match_id,
        match_date,
        competition_code,
        competition_name,
        season,
        status,
        is_played,
        home_team,
        away_team,
        home_goals,
        away_goals,
        result
    from {{ ref('stg_matches') }}

),

team_context as (

    select
        match_id,
        team,
        home_away,
        prior_played_matches,
        prior_played_matches_same_side
    from {{ ref('int_team_match_results') }}

),

home_context as (
    select * from team_context where home_away = 'HOME'
),

away_context as (
    select * from team_context where home_away = 'AWAY'
),

overall_form as (
    select * from {{ ref('int_team_form') }}
),

side_form as (
    select * from {{ ref('int_home_away_form') }}
),

joined as (

    select
        m.match_id,
        m.match_date,
        m.competition_code,
        m.competition_name,
        m.season,
        m.status,
        m.is_played,
        m.home_team,
        m.away_team,

        -- Profondeur d'historique disponible : à filtrer côté ML plutôt qu'à
        -- deviner ici.
        hc.prior_played_matches as home_matches_played,
        ac.prior_played_matches as away_matches_played,
        hc.prior_played_matches_same_side as home_home_matches_played,
        ac.prior_played_matches_same_side as away_away_matches_played,

        hf.form_as_of as home_form_as_of,
        af.form_as_of as away_form_as_of,

        -- Forme globale
        hf.matches_in_window as home_form_matches,
        af.matches_in_window as away_form_matches,
        hf.form_points as home_points_last_5,
        af.form_points as away_points_last_5,
        hf.form_avg_points as home_avg_points_last_5,
        af.form_avg_points as away_avg_points_last_5,
        hf.form_wins as home_wins_last_5,
        af.form_wins as away_wins_last_5,
        hf.form_draws as home_draws_last_5,
        af.form_draws as away_draws_last_5,
        hf.form_losses as home_losses_last_5,
        af.form_losses as away_losses_last_5,
        hf.form_goals_for as home_goals_for_last_5,
        af.form_goals_for as away_goals_for_last_5,
        hf.form_goals_against as home_goals_against_last_5,
        af.form_goals_against as away_goals_against_last_5,
        hf.form_goal_difference as home_goal_diff_last_5,
        af.form_goal_difference as away_goal_diff_last_5,
        hf.form_avg_goals_for as home_avg_goals_for_last_5,
        af.form_avg_goals_for as away_avg_goals_for_last_5,
        hf.form_avg_goals_against as home_avg_goals_against_last_5,
        af.form_avg_goals_against as away_avg_goals_against_last_5,

        -- Forme dans le même contexte : domicile pour le receveur, extérieur
        -- pour le visiteur. Ce sont ces six colonnes que le modèle consomme.
        hs.matches_in_window as home_home_form_matches,
        asf.matches_in_window as away_away_form_matches,
        hs.form_avg_points as home_home_avg_points_last_5,
        asf.form_avg_points as away_away_avg_points_last_5,
        hs.form_avg_goals_for as home_home_avg_goals_for_last_5,
        asf.form_avg_goals_for as away_away_avg_goals_for_last_5,
        hs.form_avg_goals_against as home_home_avg_goals_against_last_5,
        asf.form_avg_goals_against as away_away_avg_goals_against_last_5,

        -- Cibles. Le préfixe target_ n'est pas décoratif : il permet à un
        -- consommateur d'exclure d'un coup tout ce qui n'est connu qu'après le
        -- coup de sifflet final. Aucune feature ci-dessus n'en dérive.
        m.home_goals as target_home_goals,
        m.away_goals as target_away_goals,
        m.result as target_result

    from matches as m

    inner join home_context as hc
        on hc.match_id = m.match_id
    inner join away_context as ac
        on ac.match_id = m.match_id

    left join overall_form as hf
        on hf.team = m.home_team
        and hf.competition_code = m.competition_code
        and hf.season = m.season
        and hf.played_seq = hc.prior_played_matches

    left join overall_form as af
        on af.team = m.away_team
        and af.competition_code = m.competition_code
        and af.season = m.season
        and af.played_seq = ac.prior_played_matches

    left join side_form as hs
        on hs.team = m.home_team
        and hs.competition_code = m.competition_code
        and hs.season = m.season
        and hs.home_away = 'HOME'
        and hs.played_seq_same_side = hc.prior_played_matches_same_side

    left join side_form as asf
        on asf.team = m.away_team
        and asf.competition_code = m.competition_code
        and asf.season = m.season
        and asf.home_away = 'AWAY'
        and asf.played_seq_same_side = ac.prior_played_matches_same_side

)

select * from joined
