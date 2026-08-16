"""
Small, deterministic, hand-built fixture data -- never the real CSVs. Every
value here exists so a specific test can assert something exact about it;
see the comment next to each row.
"""
from datetime import date, datetime, timezone

# --- cot_obs -----------------------------------------------------------
# (report_date, series, release_ts, value, revision)
COT_ROWS = [
    # report_date 2026-01-06 is revised a week after its first release:
    # revision 0 published 2026-01-09, revision 1 (a correction) published
    # 2026-01-16. Same observation, two answers, driven by when you ask.
    (date(2026, 1, 6), "comm_net", datetime(2026, 1, 9, 20, 30, tzinfo=timezone.utc), 100.0, 0),
    (date(2026, 1, 6), "comm_net", datetime(2026, 1, 16, 20, 30, tzinfo=timezone.utc), 105.0, 1),
    (date(2026, 1, 13), "comm_net", datetime(2026, 1, 16, 20, 30, tzinfo=timezone.utc), 110.0, 0),
    (date(2026, 1, 20), "comm_net", datetime(2026, 1, 23, 20, 30, tzinfo=timezone.utc), 120.0, 0),
    # a second series, to prove grouping is per (report_date, series), not
    # just per report_date.
    (date(2026, 1, 6), "oi", datetime(2026, 1, 9, 20, 30, tzinfo=timezone.utc), 5000.0, 0),
]


def insert_cot_rows(conn, rows=COT_ROWS):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO cot_obs (report_date, series, release_ts, value, revision)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (report_date, series, revision) DO NOTHING
            """,
            rows,
        )


# --- fundamental_obs -----------------------------------------------------
# (series_id, obs_date, vintage, value)
FUNDAMENTAL_ROWS = [
    # obs_date 2026-04-01 is revised: first published (vintage) 2026-05-18
    # at 1310.0, corrected 2026-06-18 to 1298.0.
    ("HOUST", date(2026, 4, 1), date(2026, 5, 18), 1310.0),
    ("HOUST", date(2026, 4, 1), date(2026, 6, 18), 1298.0),
    ("HOUST", date(2026, 5, 1), date(2026, 6, 18), 1290.0),
    ("PERMIT", date(2026, 4, 1), date(2026, 5, 20), 1400.0),
]


def insert_fundamental_rows(conn, rows=FUNDAMENTAL_ROWS):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO fundamental_obs (series_id, obs_date, vintage, value)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (series_id, obs_date, vintage) DO NOTHING
            """,
            rows,
        )


# --- futures_settle --------------------------------------------------------
# Inserted deliberately out of chronological order: JAN27 first. String-
# sorting these labels gives JAN27, NOV26, SEP26 ('J' < 'N' < 'S') -- the
# exact bug CLAUDE.md warns about. contract_start is the real sort key.
# (trade_date, contract_month, contract_start, settle, volume, open_interest, no_trade_flag, note)
FUTURES_ROWS = [
    (date(2026, 7, 29), "JAN27", date(2027, 1, 1), 642.5, 9, 35, True, ""),
    (date(2026, 7, 29), "SEP26", date(2026, 9, 1), 634.0, 1011, 7123, False, ""),
    (date(2026, 7, 29), "NOV26", date(2026, 11, 1), 635.0, 88, 1045, False, ""),
]


def insert_futures_rows(conn, rows=FUTURES_ROWS):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO futures_settle
                (trade_date, contract_month, contract_start, settle, volume, open_interest, no_trade_flag, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_date, contract_month) DO NOTHING
            """,
            rows,
        )
