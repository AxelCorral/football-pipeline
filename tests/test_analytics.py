"""Tests pour src/analytics/athena_queries.py.

Seule la conversion de types est testée ici : c'est la partie qui décide de la
forme des marts exportés depuis Athena, et la seule qui ne dépende pas d'un
appel réseau.
"""

import pandas as pd
import pytest

from src.analytics.athena_queries import _coerce_athena_types


@pytest.fixture
def raw() -> pd.DataFrame:
    """Ce qu'Athena renvoie : tout en texte, les NULL en None."""
    return pd.DataFrame(
        {
            "match_id": ["1", "2", None],
            "avg_goals": ["2.5", "3.25", None],
            "match_date": ["2025-08-15 19:00:00", "2025-08-16 15:30:00", None],
            "is_played": ["true", "false", None],
            "team": ["Arsenal FC", "AC Milan", None],
        }
    )


TYPES = {
    "match_id": "bigint",
    "avg_goals": "double",
    "match_date": "timestamp",
    "is_played": "boolean",
    "team": "varchar(255)",
}


class TestCoerceAthenaTypes:
    def test_integers_stay_nullable(self, raw):
        out = _coerce_athena_types(raw, TYPES)
        assert str(out["match_id"].dtype) == "Int64"
        assert out["match_id"].tolist()[:2] == [1, 2]
        assert pd.isna(out["match_id"].iloc[2])

    def test_floats_become_numeric(self, raw):
        out = _coerce_athena_types(raw, TYPES)
        assert out["avg_goals"].iloc[1] == pytest.approx(3.25)

    def test_timestamps_become_datetimes(self, raw):
        out = _coerce_athena_types(raw, TYPES)
        assert pd.api.types.is_datetime64_any_dtype(out["match_date"])

    def test_booleans_become_nullable_booleans(self, raw):
        out = _coerce_athena_types(raw, TYPES)
        assert out["is_played"].tolist()[:2] == [True, False]
        assert pd.isna(out["is_played"].iloc[2])

    def test_parameterised_varchar_is_left_alone(self, raw):
        out = _coerce_athena_types(raw, TYPES)
        assert out["team"].iloc[0] == "Arsenal FC"

    def test_unknown_type_is_left_alone(self, raw):
        out = _coerce_athena_types(raw, {"team": "array(varchar)"})
        assert out["team"].iloc[0] == "Arsenal FC"

    def test_column_absent_from_the_result_is_ignored(self, raw):
        out = _coerce_athena_types(raw, {"absent": "bigint"})
        assert list(out.columns) == list(raw.columns)
