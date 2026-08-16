"""
TEST 1 -- the as-of query never returns anything published after the cutoff.

This is the repo's entire claim, made executable: for a grid of as_of values
spanning the fixture range, every row returned by as_of_cot / as_of_fundamentals
must match an independent Python reference model that filters on
known_col <= as_of by construction. If a row ever leaked across the cutoff,
the DB result would disagree with the reference and this test would go red.
This is the one that must never go red.

TEST 2 -- revisions are actually honoured, further down this file.
"""
from datetime import date, datetime, time, timezone

import pytest

from app import queries
from tests.fixtures import COT_ROWS, FUNDAMENTAL_ROWS, insert_cot_rows, insert_fundamental_rows


def _expected(rows, *, valid, series, known, value, tiebreak, as_of):
    """Independent reference implementation of the as-of/DISTINCT ON
    semantics in app/queries.py::_as_of_sql, evaluated in pure Python
    against the fixture rows we inserted ourselves."""
    best = {}
    for r in rows:
        if known(r) > as_of:
            continue
        key = (valid(r), series(r))
        tb = tiebreak(r)
        if key not in best or tb > best[key][0]:
            best[key] = (tb, value(r))
    return {key: v for key, (_, v) in best.items()}


COT_GRID = [
    datetime(2026, 1, 9, 20, 0, tzinfo=timezone.utc),  # before any release
    datetime(2026, 1, 9, 20, 30, tzinfo=timezone.utc),  # exactly at the first release
    datetime(2026, 1, 13, 0, 0, tzinfo=timezone.utc),  # between releases
    datetime(2026, 1, 16, 20, 30, tzinfo=timezone.utc),  # exactly at the revision + 2nd report
    datetime(2026, 1, 20, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 1, 23, 20, 30, tzinfo=timezone.utc),  # exactly at the last release
    datetime(2026, 1, 24, 0, 0, tzinfo=timezone.utc),  # after everything
]


@pytest.mark.parametrize("as_of", COT_GRID)
def test_as_of_cot_never_leaks_future_rows(pg_conn, as_of):
    insert_cot_rows(pg_conn)
    got = {(r[0], r[1]): r[2] for r in queries.as_of_cot(pg_conn, as_of)}
    expected = _expected(
        COT_ROWS,
        valid=lambda r: r[0],
        series=lambda r: r[1],
        known=lambda r: r[2],
        value=lambda r: r[3],
        tiebreak=lambda r: r[4],
        as_of=as_of,
    )
    assert got == expected


FUNDAMENTALS_GRID = [
    date(2026, 5, 17),  # before any vintage
    date(2026, 5, 18),  # exactly at the first HOUST vintage
    date(2026, 5, 19),
    date(2026, 5, 20),  # exactly at the PERMIT vintage
    date(2026, 6, 1),
    date(2026, 6, 18),  # exactly at the HOUST revision
    date(2026, 6, 19),  # after everything
]


@pytest.mark.parametrize("as_of_date", FUNDAMENTALS_GRID)
def test_as_of_fundamentals_never_leaks_future_rows(pg_conn, as_of_date):
    insert_fundamental_rows(pg_conn)
    as_of_dt = datetime.combine(as_of_date, time.max, tzinfo=timezone.utc)
    got = {}
    for series in {"HOUST", "PERMIT"}:
        for r in queries.as_of_fundamentals(pg_conn, as_of_dt, series):
            got[(r[0], r[1])] = r[2]
    expected = _expected(
        FUNDAMENTAL_ROWS,
        valid=lambda r: r[1],
        series=lambda r: r[0],
        known=lambda r: r[2],
        value=lambda r: r[3],
        tiebreak=lambda r: r[2],  # fundamental_obs has no revision column; vintage is its own tiebreak
        as_of=as_of_date,
    )
    assert got == expected


# --- TEST 2 ------------------------------------------------------------


def test_revision_is_honoured_on_fundamentals(pg_conn):
    """One obs_date, two vintages, two different values. as_of before the
    second vintage must return the first value; as_of after it must return
    the second. Same observation, two answers, driven only by when you ask."""
    insert_fundamental_rows(pg_conn)

    before = {
        r[0]: r[2]
        for r in queries.as_of_fundamentals(pg_conn, datetime(2026, 5, 19, tzinfo=timezone.utc), "HOUST")
    }
    after = {
        r[0]: r[2]
        for r in queries.as_of_fundamentals(pg_conn, datetime(2026, 6, 19, tzinfo=timezone.utc), "HOUST")
    }

    obs_date = date(2026, 4, 1)
    assert before[obs_date] == 1310.0
    assert after[obs_date] == 1298.0
    assert before[obs_date] != after[obs_date]


def test_revision_is_honoured_on_cot(pg_conn):
    """Same guarantee, on cot_obs's revision column instead of vintage."""
    insert_cot_rows(pg_conn)

    before = {r[0]: r[2] for r in queries.as_of_cot(pg_conn, datetime(2026, 1, 10, tzinfo=timezone.utc), "comm_net")}
    after = {r[0]: r[2] for r in queries.as_of_cot(pg_conn, datetime(2026, 1, 17, tzinfo=timezone.utc), "comm_net")}

    report_date = date(2026, 1, 6)
    assert before[report_date] == 100.0
    assert after[report_date] == 105.0
    assert before[report_date] != after[report_date]
