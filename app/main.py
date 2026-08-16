"""
FastAPI entrypoint. Run: uvicorn app.main:app --reload

Every route in this repo is `def`, not `async def` -- psycopg's sync driver
blocks, and FastAPI runs plain `def` handlers in a threadpool automatically.
An `async def` handler making a blocking DB call would stall the whole event
loop instead -- the one real gotcha with a blocking driver under FastAPI.

/docs (Swagger) and /redoc are free -- generated from the type hints and
response_model= declarations below, no extra work. Every endpoint can be
exercised there without reading a line of this code.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse
from app.routers import cot, fundamentals, futures, physical

app = FastAPI(
    title="lbr-pit",
    description=(
        "Point-in-time lumber futures, COT and fundamentals. Every table carries two time "
        "axes -- what a value describes, and when it became knowable -- and one as-of query "
        "serves all of them. See README.md for the query and its mirror."
    ),
)

# React dev server (Vite) is a different origin -- without this, frontend
# fetches fail with an error that never names the actual cause.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(futures.router)
app.include_router(cot.router)
app.include_router(fundamentals.router)
app.include_router(physical.router)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")
