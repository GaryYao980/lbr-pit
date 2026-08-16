"""
TEST 3 -- first_published is the mirror, not a duplicate.

first_published_fundamentals must return the earliest vintage per obs_date,
and it must differ from the as_of=today result on at least one row in the
fixture. If those two ever agree everywhere, the headline "as first
published vs current" chart is meaningless -- it would just be drawing the
same line twice -- so this test fails loudly rather than passing quietly.
"""
from datetime import date, datetime, timezone

from app import queries
from tests.fixtures import insert_fundamental_rows


def test_first_published_is_earliest_vintage_and_differs_from_current(pg_conn):
    insert_fundamental_rows(pg_conn)

    first = {r[0]: r[2] for r in queries.first_published_fundamentals(pg_conn, "HOUST")}
    current = {
        r[0]: r[2]
        for r in queries.as_of_fundamentals(pg_conn, datetime(2026, 12, 31, tzinfo=timezone.utc), "HOUST")
    }

    obs_date = date(2026, 4, 1)
    assert first[obs_date] == 1310.0  # earliest vintage: 2026-05-18
    assert current[obs_date] == 1298.0  # latest vintage: 2026-06-18

    assert first != current, "first_published and as_of=today agree on every row -- the mirror is a duplicate"
