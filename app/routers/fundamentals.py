from datetime import date, datetime, time, timezone

import psycopg
from fastapi import APIRouter, Depends

from app import queries
from app.deps import get_db
from app.models import (
    FundamentalComparePoint,
    FundamentalCompareResponse,
    FundamentalObservation,
    FundamentalVintage,
)

router = APIRouter(prefix="/api", tags=["fundamentals"])


@router.get("/fundamentals", response_model=list[FundamentalObservation])
def get_fundamentals(series: str = "HOUST", as_of: date = date.today(), conn: psycopg.Connection = Depends(get_db)):
    """ALFRED vintage-aware as-of query -- same shape as /api/cot, different table."""
    as_of_ts = datetime.combine(as_of, time.max)
    rows = queries.as_of_fundamentals(conn, as_of_ts, series)
    return [FundamentalObservation(obs_date=r[0], value=r[2]) for r in rows]


@router.get("/fundamentals/first", response_model=FundamentalCompareResponse)
def get_fundamentals_first(series: str = "HOUST", conn: psycopg.Connection = Depends(get_db)):
    """the headline panel. 'As first published' vs 'current' (as_of=far future),
    same function as /api/cot's as-of query with the sort direction flipped."""
    first = {r[0]: r[2] for r in queries.first_published_fundamentals(conn, series)}
    current = {r[0]: r[2] for r in queries.as_of_fundamentals(conn, datetime.now(timezone.utc), series)}
    common = sorted(set(first) & set(current))
    note = None
    if not common:
        note = "fundamental_obs has no rows for this series -- the loader has not been run. See etl/load_fundamentals.py (needs FRED_API_KEY)."
    return FundamentalCompareResponse(
        series=series,
        note=note,
        points=[FundamentalComparePoint(obs_date=d, first_published=first[d], current=current[d]) for d in common],
    )


@router.get("/fundamentals/vintages", response_model=list[FundamentalVintage])
def get_fundamentals_vintages(series: str = "HOUST", obs_date: date = date.today(), conn: psycopg.Connection = Depends(get_db)):
    rows = queries.fundamental_vintages(conn, series, obs_date)
    return [FundamentalVintage(vintage=r[0], value=r[1]) for r in rows]
