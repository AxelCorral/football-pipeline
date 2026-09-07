{#
    Fenêtre glissante commune à tous les modèles de forme.

    Le cadre couvre les `form_window` derniers matchs joués, match courant
    INCLUS. C'est volontaire : `int_team_form` et `int_home_away_form` décrivent
    l'état d'une équipe APRÈS son n-ième match joué, pas avant.

    L'absence de fuite ne vient donc pas du cadre mais de la jointure faite en
    aval : un match M est rattaché à la ligne de forme dont le rang vaut le
    nombre de matchs joués strictement avant M. Voir fct_match_features.sql et
    docs/dbt.md.

    Le cadre s'applique à des lignes déjà filtrées sur les matchs joués, donc
    « N lignes précédentes » et « N matchs joués précédents » sont la même chose.
#}
{% macro form_frame(partition_by) %}
    over (
        partition by {{ partition_by }}
        order by match_date, match_id
        rows between {{ var('form_window') - 1 }} preceding and current row
    )
{% endmacro %}
