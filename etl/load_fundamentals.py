"""
Pull ALFRED (vintage-aware FRED) series into fundamental_obs.

Idempotent: re-running produces the same table, never duplicates.
Natural key is (series_id, obs_date, vintage); ON CONFLICT DO NOTHING.

Uses the plain FRED API with realtime_start=1776-07-04 & realtime_end=9999-12-31,
which returns one row per historical vintage for a series -- the standard way
to pull full ALFRED history through the regular (free) FRED endpoint.

Requires FRED_API_KEY. Without one this loader refuses to run and writes
nothing -- see CLAUDE.md: synthetic data may live in exploration notebooks,
never behind an API route.
"""
import json
import os
import sys
import urllib.error
import urllib.request

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://lbrpit:lbrpit@localhost:5432/lbrpit")
FRED_API_KEY = os.environ.get("FRED_API_KEY")

SERIES_IDS = ["HOUST", "HOUST1F", "PERMIT", "MORTGAGE30US", "WPU081", "DEXCAUS"]

NO_KEY_MESSAGE = """\
FRED_API_KEY is not set -- refusing to run.

This loader pulls ALFRED vintage history for HOUST, HOUST1F, PERMIT,
MORTGAGE30US, WPU081, and DEXCAUS into fundamental_obs, which feeds the
fundamentals panel. Get a free key here:
  https://fred.stlouisfed.org/docs/api/api_key.html

The COT and futures panels do not need this key and work without it.
"""


def fetch_alfred(series_id: str, api_key: str):
    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
        "&realtime_start=1776-07-04&realtime_end=9999-12-31"
    )
    with urllib.request.urlopen(url, timeout=15) as resp:
        payload = json.load(resp)
    rows = []
    for obs in payload["observations"]:
        if obs["value"] in ("", "."):
            continue
        rows.append((series_id, obs["date"], obs["realtime_start"], float(obs["value"])))
    return rows


def load(conn: psycopg.Connection) -> tuple[int, int]:
    rows = []
    for series_id in SERIES_IDS:
        rows.extend(fetch_alfred(series_id, FRED_API_KEY))

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM fundamental_obs")
        before = cur.fetchone()[0]

        cur.executemany(
            """
            INSERT INTO fundamental_obs (series_id, obs_date, vintage, value)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (series_id, obs_date, vintage) DO NOTHING
            """,
            rows,
        )
        conn.commit()

        cur.execute("SELECT count(*) FROM fundamental_obs")
        after = cur.fetchone()[0]

    return before, after


def main():
    if not FRED_API_KEY:
        print(NO_KEY_MESSAGE)
        sys.exit(1)

    with psycopg.connect(DATABASE_URL) as conn:
        try:
            before, after = load(conn)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"ALFRED fetch failed: {e!r}")
            sys.exit(1)
        print(f"fundamental_obs: {before} -> {after} rows")


if __name__ == "__main__":
    main()
