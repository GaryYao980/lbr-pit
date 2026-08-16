"""
Load lbr_term_structure_cme.csv into futures_settle.

Idempotent: re-running produces the same table, never duplicates.
Natural key is (trade_date, contract_month); ON CONFLICT DO NOTHING.

Data quirk, found and fixed while parsing the real file:
the source CSV's `note` column is unquoted and itself contains commas
("zero volume, zero OI, ..."), which breaks a naive `csv`/pandas parse. Each
line is split on the first 7 commas only, so anything after that stays in
`note` verbatim.
"""
import os
import sys
from datetime import date
from pathlib import Path

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://lbrpit:lbrpit@localhost:5432/lbrpit")
DATA_DIR = Path(os.environ.get("LBR_PIT_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
CSV_PATH = DATA_DIR / "lbr_term_structure_cme.csv"

TERM_COLS = ["trade_date", "month", "settle", "change", "volume", "open_interest", "no_trade_flag", "note"]

# contract codes are labels, not sort keys. Computed once at load and
# stored, so no consumer has to parse a string to order a curve. Explicit dict
# rather than strptime("%b") because %b is locale-dependent.
LBR_MONTHS = {"JAN": 1, "MAR": 3, "MAY": 5, "JUL": 7, "SEP": 9, "NOV": 11}


def contract_start(code: str) -> date:
    """'SEP26' -> date(2026, 9, 1). Raises on an unknown month rather than
    guessing -- a silently mis-sorted curve is worse than a failed load."""
    mon, yr = code[:3].upper(), code[3:]
    if mon not in LBR_MONTHS:
        raise ValueError(f"unknown LBR contract month in {code!r}; expected one of {sorted(LBR_MONTHS)}")
    return date(2000 + int(yr), LBR_MONTHS[mon], 1)


def parse_term_structure(csv_path: Path):
    rows = []
    with open(csv_path) as fh:
        next(fh)  # header
        for line in fh:
            parts = line.rstrip("\n").split(",", 7)
            rows.append(dict(zip(TERM_COLS, parts)))
    return rows


def load(conn: psycopg.Connection) -> tuple[int, int]:
    rows = parse_term_structure(CSV_PATH)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM futures_settle")
        before = cur.fetchone()[0]

        for r in rows:
            cur.execute(
                """
                INSERT INTO futures_settle
                    (trade_date, contract_month, contract_start, settle, volume, open_interest, no_trade_flag, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trade_date, contract_month) DO NOTHING
                """,
                (
                    r["trade_date"],
                    r["month"],
                    contract_start(r["month"]),
                    float(r["settle"]),
                    int(r["volume"]),
                    int(r["open_interest"]),
                    r["no_trade_flag"] == "1",
                    r["note"],
                ),
            )
        conn.commit()

        cur.execute("SELECT count(*) FROM futures_settle")
        after = cur.fetchone()[0]
    return before, after


def main():
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found. Set LBR_PIT_DATA_DIR to the folder holding the source CSVs.")
        sys.exit(1)

    with psycopg.connect(DATABASE_URL) as conn:
        before, after = load(conn)
        print(f"futures_settle: {before} -> {after} rows")


if __name__ == "__main__":
    main()
