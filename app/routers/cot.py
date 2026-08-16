from datetime import date, datetime, time

import psycopg
from fastapi import APIRouter, Depends

from app import queries
from app.deps import get_db
from app.models import CotObservation, CotRevisionPoint, CotRevisionsResponse

router = APIRouter(prefix="/api", tags=["cot"])


@router.get("/cot", response_model=list[CotObservation])
def get_cot(as_of: date, series: str = "nonc_net", conn: psycopg.Connection = Depends(get_db)):
    """The as-of query, exposed. Dragging `as_of` backwards makes the most
    recent report_date disappear once it's earlier than that report's
    release_ts -- this is the mechanism the frontend's as-of slider drives."""
    as_of_ts = datetime.combine(as_of, time.max)
    rows = queries.as_of_cot(conn, as_of_ts, series=series)
    return [CotObservation(report_date=r[0], series=r[1], value=r[2]) for r in rows]


@router.get("/cot/revisions", response_model=CotRevisionsResponse)
def get_cot_revisions(series: str = "nonc_net", conn: psycopg.Connection = Depends(get_db)):
    rows = queries.cot_revisions(conn, series)
    return CotRevisionsResponse(
        series=series,
        note=(
            "cot_lumber_clean.csv has no revision history -- every row's revision=0, "
            "so as_known and final are identical here by construction. The real "
            "divergence this endpoint's shape is meant to show is demonstrated on "
            "/api/fundamentals/first vs /api/fundamentals (HOUST has real ALFRED revisions)."
        ),
        points=[CotRevisionPoint(report_date=r[0], as_known=r[1], final=r[2]) for r in rows],
    )
