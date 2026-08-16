"""Pydantic response models -- the contract between backend and frontend
(declare response_model= on every route so the two can't drift)."""
from datetime import date
from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class ContractResponse(BaseModel):
    contract_month: str


class CurvePoint(BaseModel):
    month: str
    settle: float
    volume: int
    open_interest: int
    no_trade_flag: bool  # render differently, don't plot as a real trade


class SettlementPoint(BaseModel):
    trade_date: date
    contract_month: str
    settle: float
    volume: int
    open_interest: int
    no_trade_flag: bool


class SpreadPoint(BaseModel):
    trade_date: date
    leg1_settle: float
    leg2_settle: float
    spread: float


class ContinuousPoint(BaseModel):
    trade_date: date
    settle: float


class ContinuousResponse(BaseModel):
    adjust: str
    roll: str
    roll_date: Optional[date]
    roll_note: Optional[str]  # e.g. "no volume crossover in this window" -- flagged, not hidden
    points: list[ContinuousPoint]


class CotObservation(BaseModel):
    report_date: date
    series: str
    value: float


class CotRevisionPoint(BaseModel):
    report_date: date
    as_known: float
    final: float


class CotRevisionsResponse(BaseModel):
    series: str
    note: str  # this dataset has no real COT revisions -- see queries.py
    points: list[CotRevisionPoint]


class FundamentalObservation(BaseModel):
    obs_date: date
    value: float


class FundamentalComparePoint(BaseModel):
    obs_date: date
    first_published: float
    current: float


class FundamentalCompareResponse(BaseModel):
    series: str
    note: Optional[str] = None  # set when fundamental_obs has no rows for this series
    points: list[FundamentalComparePoint]


class FundamentalVintage(BaseModel):
    vintage: date
    value: float


class PhysicalStatusResponse(BaseModel):
    schema_ready: bool = True
    row_count: int = 0
    source: str = "Fastmarkets — requires a licensed data feed"
