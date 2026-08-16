import psycopg
from fastapi import APIRouter, Depends

from app import queries
from app.deps import get_db
from app.models import PhysicalStatusResponse

router = APIRouter(prefix="/api", tags=["physical"])


@router.get("/physical/status", response_model=PhysicalStatusResponse)
def get_physical_status(conn: psycopg.Connection = Depends(get_db)):
    """the deliberate hole. Schema is real; row_count should be 0.
    If this ever returns nonzero, something upstream started faking physical
    prices, which is exactly what this endpoint exists to make impossible to
    do quietly."""
    count = queries.physical_row_count(conn)
    return PhysicalStatusResponse(schema_ready=True, row_count=count)
