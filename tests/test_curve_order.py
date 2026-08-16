"""
TEST 4 -- contract months order by time, not label.

SEP26, NOV26, JAN27 are inserted out of chronological order (see
tests/fixtures.py); curve() must still return them SEP26, NOV26, JAN27.
The failure this guards against put JAN27 before SEP26 -- string-sorting
'JAN27' < 'NOV26' < 'SEP26' -- and produced a sawtooth that does not exist
in the market.
"""
from datetime import date

from app import queries
from tests.fixtures import insert_futures_rows


def test_curve_orders_by_contract_start_not_label(pg_conn):
    insert_futures_rows(pg_conn)

    rows = queries.curve(pg_conn, date(2026, 7, 29))
    months = [r[0] for r in rows]

    assert months == ["SEP26", "NOV26", "JAN27"]
