"""
All SQL lives here, not inline in the route handlers.

The two core queries are generic in shape across cot_obs and
fundamental_obs -- both tables are (valid_date, known_date, series, value).
Rather than write raw SQL twice, `_as_of_sql` / `_first_published_sql` take
the table/column names as trusted, hardcoded-by-caller strings (never user
input) and build the query once. Roll logic for continuous() is procedural
(volume-crossover / LTD-approximation), not expressible as a single query,
so it fetches both legs and applies the rule in Python -- same logic already
validated against the real CSVs before being ported here.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import psycopg

# ---------------------------------------------------------------------------
# Generic as-of / first-published # ---------------------------------------------------------------------------

def _as_of_sql(table: str, valid_col: str, known_col: str, series_col: str, value_col: str, revision_col: Optional[str]) -> str:
    order_tiebreak = revision_col or known_col
    return f"""
        SELECT DISTINCT ON ({valid_col}, {series_col})
               {valid_col} AS valid_date, {series_col} AS series, {value_col} AS value
        FROM   {table}
        WHERE  {known_col} <= %(as_of)s
               {{series_filter}}
        ORDER  BY {valid_col}, {series_col}, {order_tiebreak} DESC
    """


def _first_published_sql(table: str, valid_col: str, known_col: str, series_col: str, value_col: str) -> str:
    return f"""
        SELECT DISTINCT ON ({valid_col}, {series_col})
               {valid_col} AS valid_date, {series_col} AS series, {value_col} AS value
        FROM   {table}
        {{series_filter}}
        ORDER  BY {valid_col}, {series_col}, {known_col} ASC
    """


def as_of_cot(conn: psycopg.Connection, as_of: datetime, series: Optional[str] = None):
    """The eight-line as-of query, against cot_obs."""
    sql = _as_of_sql("cot_obs", "report_date", "release_ts", "series", "value", "revision")
    params = {"as_of": as_of}
    series_filter = ""
    if series:
        series_filter = "AND series = %(series)s"
        params["series"] = series
    with conn.cursor() as cur:
        cur.execute(sql.format(series_filter=series_filter), params)
        return cur.fetchall()  # (valid_date, series, value)


def as_of_fundamentals(conn: psycopg.Connection, as_of: datetime, series: str):
    """Same shape as as_of_cot, against fundamental_obs ('one function, two tables')."""
    sql = _as_of_sql("fundamental_obs", "obs_date", "vintage", "series_id", "value", None)
    params = {"as_of": as_of, "series": series}
    with conn.cursor() as cur:
        cur.execute(sql.format(series_filter="AND series_id = %(series)s"), params)
        return cur.fetchall()


def first_published_fundamentals(conn: psycopg.Connection, series: str):
    """earliest vintage per obs_date -- the headline-chart query."""
    sql = _first_published_sql("fundamental_obs", "obs_date", "vintage", "series_id", "value")
    with conn.cursor() as cur:
        cur.execute(sql.format(series_filter="WHERE series_id = %(series)s"), {"series": series})
        return cur.fetchall()


def fundamental_vintages(conn: psycopg.Connection, series: str, obs_date: date):
    """Every vintage on record for one obs_date -- the revision history of a single number."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT vintage, value FROM fundamental_obs
            WHERE series_id = %s AND obs_date = %s
            ORDER BY vintage
            """,
            (series, obs_date),
        )
        return cur.fetchall()


def cot_revisions(conn: psycopg.Connection, series: str):
    """GET /api/cot/revisions -> 'as-known vs final, both series'.

    NOTE: cot_lumber_clean.csv (this demo's only COT source) has no revision
    history -- every row's `revision` is 0, so 'as first known' and 'final'
    are mathematically identical here. Returned anyway to match the API
    contract; the actual divergence this endpoint is meant to show is
    demonstrated for real on the fundamentals panel (§3a, HOUST), where
    ALFRED revisions are real. Flagged in the response's `note` field, not
    silently faked.
    """
    as_known = _as_of_sql("cot_obs", "report_date", "release_ts", "series", "value", "revision")
    with conn.cursor() as cur:
        cur.execute(
            as_known.format(series_filter="AND series = %(series)s"),
            {"as_of": datetime.now(timezone.utc), "series": series},
        )
        final_rows = {r[0]: r[2] for r in cur.fetchall()}
    # "as known" = same query at release_ts + 0 (i.e. immediately on release) since
    # there is no earlier partial-knowledge state in this dataset; identical to final.
    return [(rd, val, val) for rd, val in final_rows.items()]


# ---------------------------------------------------------------------------
# Futures: curve, spread, continuous # ---------------------------------------------------------------------------

LBR_MONTHS = {"JAN": 1, "MAR": 3, "MAY": 5, "JUL": 7, "SEP": 9, "NOV": 11}


def resolve_leg(conn: psycopg.Connection, token: str) -> str:
    """'N1'/'N2'/'N3' mean the nth listed contract by contract_start,
    resolved in SQL. An explicit code like 'SEP26' passes through unchanged.

    Relative legs are resolved against the most recent trade date and then held
    fixed for the series -- a genuinely rolling spread is a different object and
    is out of scope here. The resolved codes are returned to the caller so the
    API can state which months it actually used rather than leaving it implied.
    """
    t = token.strip().upper()
    if not (t.startswith("N") and t[1:].isdigit()):
        return t
    n = int(t[1:])
    if n < 1:
        raise ValueError("relative legs are 1-indexed: N1 is the front month")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT contract_month FROM futures_settle
            WHERE trade_date = (SELECT max(trade_date) FROM futures_settle)
            ORDER BY contract_start
            OFFSET %s LIMIT 1
            """,
            (n - 1,),
        )
        row = cur.fetchone()
    if row is None:
        raise ValueError(f"{token} does not exist on the latest trade date")
    return row[0]

def curve(conn: psycopg.Connection, trade_date: date):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT contract_month, settle, volume, open_interest, no_trade_flag
            FROM futures_settle
            WHERE trade_date = %s
            ORDER BY contract_start          -- never ORDER BY the label
            """,
            (trade_date,),
        )
        return cur.fetchall()


def contracts(conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ON (contract_start) contract_month FROM futures_settle ORDER BY contract_start")
        return [r[0] for r in cur.fetchall()]


def settlements(conn: psycopg.Connection, start: Optional[date], end: Optional[date], months: Optional[list[str]]):
    clauses, params = [], []
    if start:
        clauses.append("trade_date >= %s")
        params.append(start)
    if end:
        clauses.append("trade_date <= %s")
        params.append(end)
    if months:
        clauses.append("contract_month = ANY(%s)")
        params.append(months)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT trade_date, contract_month, settle, volume, open_interest, no_trade_flag
            FROM futures_settle {where} ORDER BY trade_date, contract_start
            """,
            params,
        )
        return cur.fetchall()


def _leg_series(conn: psycopg.Connection, month: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT trade_date, settle, volume FROM futures_settle WHERE contract_month = %s ORDER BY trade_date",
            (month,),
        )
        return cur.fetchall()  # [(trade_date, settle, volume), ...]


def spread(conn: psycopg.Connection, leg1: str, leg2: str):
    a = {r[0]: r[1] for r in _leg_series(conn, leg1)}
    b = {r[0]: r[1] for r in _leg_series(conn, leg2)}
    out = []
    for trade_date in sorted(set(a) & set(b)):
        out.append((trade_date, a[trade_date], b[trade_date], a[trade_date] - b[trade_date]))
    return out


def continuous(
    conn: psycopg.Connection,
    front: str,
    back: str,
    roll: str = "volume",
    adjust: str = "none",
    n_days_before_ltd: int = 5,
    assumed_ltd_day_of_month: int = 16,
):
    """roll is a RULE (`volume` | `ltd`), not a hard-coded date.
    Validated against the real term-structure CSV before being ported here;
    ported here unchanged except reading from Postgres instead of the CSV.
    """
    f_rows = _leg_series(conn, front)   # (trade_date, settle, volume)
    b_rows = _leg_series(conn, back)
    f_by_date = {r[0]: r for r in f_rows}
    b_by_date = {r[0]: r for r in b_rows}
    common_dates = sorted(set(f_by_date) & set(b_by_date))

    note = None
    if roll == "volume":
        crossover_dates = [d for d in common_dates if b_by_date[d][2] > f_by_date[d][2]]
        if not crossover_dates:
            roll_date = max(common_dates) if common_dates else None
            note = (
                f"no volume crossover observed in this {len(common_dates)}-day window "
                "(back month never out-traded front month) -- fell back to the last "
                "available date; real data would very likely show a real crossover"
            )
        else:
            roll_date = min(crossover_dates)
    elif roll == "ltd":
        mon_str, yr_str = front[:3].upper(), front[3:]
        if mon_str not in LBR_MONTHS:
            raise ValueError(f"unknown LBR contract month in {front!r}")
        mon_num = LBR_MONTHS[mon_str]      # explicit: strptime("%b") is locale-dependent
        year = 2000 + int(yr_str)
        assumed_ltd = date(year, mon_num, assumed_ltd_day_of_month)
        roll_date = assumed_ltd - timedelta(days=n_days_before_ltd)
        note = f"APPROXIMATED: no official LTD calendar in this dataset; assumed LTD={assumed_ltd.isoformat()}"
    else:
        raise ValueError("roll must be 'volume' or 'ltd'")

    f_dates = [r[0] for r in f_rows]
    b_dates = [r[0] for r in b_rows]
    pre = [(d, f_by_date[d][1]) for d in f_dates if roll_date and d < roll_date]
    post = [(d, b_by_date[d][1]) for d in b_dates if roll_date and d >= roll_date]

    if adjust == "ratio" and roll_date and roll_date in f_by_date and roll_date in b_by_date:
        ratio = b_by_date[roll_date][1] / f_by_date[roll_date][1]
        pre = [(d, settle * ratio) for d, settle in pre]

    points = sorted(pre + post, key=lambda x: x[0])
    return points, roll_date, note


# ---------------------------------------------------------------------------
# Physical # ---------------------------------------------------------------------------

def physical_row_count(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM physical_price")
        return cur.fetchone()[0]
