from datetime import date
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from app import queries
from app.deps import get_db
from app.models import (
    ContinuousPoint,
    ContinuousResponse,
    CurvePoint,
    SettlementPoint,
    SpreadPoint,
)

router = APIRouter(prefix="/api", tags=["futures"])


@router.get("/contracts", response_model=list[str])
def get_contracts(conn: psycopg.Connection = Depends(get_db)):
    return queries.contracts(conn)


@router.get("/settlements", response_model=list[SettlementPoint])
def get_settlements(
    start: Optional[date] = None,
    end: Optional[date] = None,
    months: Optional[list[str]] = Query(default=None),
    conn: psycopg.Connection = Depends(get_db),
):
    rows = queries.settlements(conn, start, end, months)
    return [
        SettlementPoint(trade_date=r[0], contract_month=r[1], settle=r[2], volume=r[3], open_interest=r[4], no_trade_flag=r[5])
        for r in rows
    ]


@router.get("/curve", response_model=list[CurvePoint])
def get_curve(trade_date: date, conn: psycopg.Connection = Depends(get_db)):
    rows = queries.curve(conn, trade_date)
    if not rows:
        raise HTTPException(status_code=404, detail=f"no curve data for {trade_date}")
    return [CurvePoint(month=r[0], settle=r[1], volume=r[2], open_interest=r[3], no_trade_flag=r[4]) for r in rows]


@router.get("/spreads", response_model=list[SpreadPoint])
def get_spread(legs: str, conn: psycopg.Connection = Depends(get_db)):
    """legs accepts either explicit codes ('SEP26-NOV26') or relative positions
    ('N1-N2'). Relative legs are resolved by contract_start, never by sorting
    the label -- see the notes above and queries.resolve_leg."""
    parts = legs.split("-")
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="legs must be 'A-B', e.g. 'N1-N2' or 'SEP26-NOV26'")
    try:
        leg1, leg2 = (queries.resolve_leg(conn, p) for p in parts)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    rows = queries.spread(conn, leg1, leg2)
    return [SpreadPoint(trade_date=r[0], leg1_settle=r[1], leg2_settle=r[2], spread=r[3]) for r in rows]


@router.get("/continuous", response_model=ContinuousResponse)
def get_continuous(
    front: str = "SEP26",
    back: str = "NOV26",
    adjust: str = Query(default="none", pattern="^(none|ratio)$"),
    roll: str = Query(default="volume", pattern="^(volume|ltd)$"),
    conn: psycopg.Connection = Depends(get_db),
):
    points, roll_date, note = queries.continuous(conn, front, back, roll=roll, adjust=adjust)
    return ContinuousResponse(
        adjust=adjust,
        roll=roll,
        roll_date=roll_date,
        roll_note=note,
        points=[ContinuousPoint(trade_date=d, settle=s) for d, s in points],
    )
