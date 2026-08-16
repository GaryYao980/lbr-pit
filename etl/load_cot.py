"""
Load cot_lumber_clean.csv into cot_obs, deriving release_ts from report_date.

Idempotent: re-running produces the same table, never duplicates.
Natural key is (report_date, series, revision); ON CONFLICT DO NOTHING.
This source has no revision history (CFTC COT is essentially never restated),
so revision is always 0 -- the point-in-time gap comes entirely from
report_date (valid time) vs release_ts (transaction time).

release_ts derivation, and the reason it is not a flat offset: report_date is
USUALLY a Tuesday, but CFTC shifts it back a day whenever that Tuesday is a federal
holiday (2 of the 170 report dates loaded here: 2023-07-03, 2025-11-10). A flat
`report_date + 3 days` is wrong for those rows. Instead this derives "the
Friday of that report week" from whatever weekday report_date actually is.

ASSUMPTION, stated here and in etl/README.md: the release itself is always
that Friday at 15:30 ET. This is still wrong whenever that Friday is *also*
a US holiday (CFTC pushes the release to the next business day) -- 6 of the 170
weeks loaded here (2024-03-26, 2025-04-15, 2025-07-01, 2026-03-31, 2026-06-16,
2026-06-30). Real ETL should source the actual CFTC release calendar; this
derivation is a documented approximation, not a fabricated fact.

Contract scope: LUMBER only, from 2023-04-25. See the note beside CONTRACT below --
it is the most consequential decision in this file.
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://lbrpit:lbrpit@localhost:5432/lbrpit")
DATA_DIR = Path(os.environ.get("LBR_PIT_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
CSV_PATH = DATA_DIR / "cot_lumber_clean.csv"

SERIES_COLUMNS = ["oi", "comm_net", "nonc_net"]

# ---------------------------------------------------------------------------
# Contract scope, and why it is a decision rather than a filter.
#
# The source file spans two CFTC contracts: RANDOM LENGTH LUMBER (110,000 bf)
# and its replacement LUMBER (27,500 bf). They ran side by side for seven weeks,
# 2023-02-21 to 2023-04-18, and CFTC reported both.
#
# On every one of those seven weeks the two disagree on the SIGN of commercial
# net positioning -- LUMBER negative, RANDOM LENGTH LUMBER positive -- while
# RANDOM LENGTH LUMBER carries two to eight times the board-feet exposure. They
# are not two views of one number; they are two different markets during a
# handover, and no arithmetic reconciles them.
#
# `cot_obs` is keyed (report_date, series, revision) with no contract column, so
# the two cannot both live in it. That makes the scope a question the loader has
# to answer out loud: LUMBER, from the first report after RANDOM LENGTH LUMBER
# was delisted. From that date forward, LUMBER *is* the lumber market. Nothing is
# averaged and nothing is spliced.
#
# The guard below exists for the same reason. ON CONFLICT DO NOTHING can resolve
# a key collision, but it resolves it by keeping whichever row arrived first --
# an ordering accident, recorded nowhere. A series definition should be legible
# in the loader, not implied by insert order.
CONTRACT = "LUMBER"
CONTRACT_FROM = date(2023, 4, 25)  # first report date after RANDOM LENGTH LUMBER delisted


class DuplicateNaturalKey(Exception):
    """Two source rows claim the same (report_date, series, revision)."""

# CFTC COT reports are as-of Tuesday, released the following Friday ~15:30 ET.
# ET is UTC-5 (EST) / UTC-4 (EDT); using a fixed UTC-5 offset here is itself an
# approximation (misses DST) -- flagged, not hidden, same spirit as the
# report-week derivation below.
RELEASE_HOUR_UTC = 20  # 15:30 ET (EST, UTC-5) == 20:30 UTC
RELEASE_MINUTE_UTC = 30


def friday_of_report_week(report_date) -> "datetime.date":
    """The Friday of the same calendar week as report_date, regardless of
    which weekday report_date actually falls on (usually Tuesday=1,
    occasionally Monday=0 when CFTC shifts the as-of date)."""
    days_to_friday = (4 - report_date.weekday()) % 7
    return report_date + timedelta(days=days_to_friday)


def release_ts_for(report_date) -> datetime:
    friday = friday_of_report_week(report_date)
    return datetime(friday.year, friday.month, friday.day, RELEASE_HOUR_UTC, RELEASE_MINUTE_UTC, tzinfo=timezone.utc)


def parse_cot(csv_path: Path):
    import csv as csv_mod

    rows = []
    with open(csv_path) as fh:
        reader = csv_mod.DictReader(fh)
        for r in reader:
            report_date = datetime.strptime(r["date"], "%Y-%m-%d").date()

            # Contract selection, per the note above. A file without a contract
            # column is a single-contract file and passes through untouched.
            contract = r.get("contract")
            if contract is not None and contract.strip().upper() != CONTRACT:
                continue
            if report_date < CONTRACT_FROM:
                continue

            release_ts = release_ts_for(report_date)
            for series in SERIES_COLUMNS:
                if r.get(series) in (None, ""):
                    continue
                rows.append((report_date, release_ts, series, float(r[series]), 0))

    # Never hand the database a set it can only resolve by discarding rows.
    # Every number here should trace to a decision that is written down, so a
    # collision is raised where it can be read rather than absorbed where it
    # cannot.
    seen, clashes = set(), set()
    for report_date, _release_ts, series, _value, revision in rows:
        key = (report_date, series, revision)
        if key in seen:
            clashes.add(key)
        seen.add(key)
    if clashes:
        sample = ", ".join(f"{d.isoformat()}/{s}/rev{rev}" for d, s, rev in sorted(clashes)[:5])
        more = "" if len(clashes) <= 5 else f" (+{len(clashes) - 5} more)"
        raise DuplicateNaturalKey(
            f"{len(clashes)} duplicate (report_date, series, revision) keys in {csv_path.name}: "
            f"{sample}{more}. ON CONFLICT DO NOTHING resolves this by keeping whichever row is "
            f"read first, which is an ordering accident. Resolve the source before loading."
        )
    return rows


def load(conn: psycopg.Connection) -> tuple[int, int]:
    rows = parse_cot(CSV_PATH)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM cot_obs")
        before = cur.fetchone()[0]

        cur.executemany(
            """
            INSERT INTO cot_obs (report_date, release_ts, series, value, revision)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (report_date, series, revision) DO NOTHING
            """,
            rows,
        )
        conn.commit()

        cur.execute("SELECT count(*) FROM cot_obs")
        after = cur.fetchone()[0]
    return before, after


def main():
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found. Set LBR_PIT_DATA_DIR to the folder holding the source CSVs.")
        sys.exit(1)

    with psycopg.connect(DATABASE_URL) as conn:
        before, after = load(conn)
        print(f"cot_obs: {before} -> {after} rows")


if __name__ == "__main__":
    main()
