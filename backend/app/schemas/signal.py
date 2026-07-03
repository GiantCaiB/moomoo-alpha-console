from datetime import datetime
from pydantic import BaseModel


class SignalScoreResponse(BaseModel):
    category: str
    score: float
    max_score: float
    details: str | None


class SignalResponse(BaseModel):
    id: str
    symbol: str
    verdict: str
    total_score: float
    scores: list[SignalScoreResponse]
    reason: str | None
    entry_min: float | None
    entry_max: float | None
    stop_level: float | None
    target_size_pct: float | None
    risk_amount: float | None
    invalidation: str | None
    current_price: float | None
    approved: bool | None
    signal_date: datetime
    created_at: datetime
