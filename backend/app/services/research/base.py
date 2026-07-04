from dataclasses import dataclass
from typing import Protocol


from datetime import datetime


@dataclass
class ScreenRequest:
    universe: list[str]
    max_results: int = 10
    min_score: float = 75.0


@dataclass
class SignalDto:
    symbol: str
    verdict: str  # BUY_STARTER, WATCH, AVOID, DATA_ERROR
    total_score: float
    scores: list[dict]  # [{category, score, max_score, details}]
    reason: str
    entry_min: float | None = None
    entry_max: float | None = None
    stop_level: float | None = None
    target_size_pct: float | None = None
    risk_amount: float | None = None
    invalidation: str | None = None
    current_price: float | None = None
    strategy_name: str = ""
    data_source: str = "mock"
    generated_at: datetime | None = None
    universe: list[str] | None = None
    price_source: str = "mock_synthetic"
    bar_source: str = "mock_generated"
    is_real_market_data: bool = False
    is_tradeable: bool = False
    has_error: bool = False
    error_message: str | None = None
    failed_filters: list[str] | None = None
    data_quality_status: str = "OK"
    calculated_score_before_filters: float | None = None


@dataclass
class ResearchReport:
    symbol: str
    summary: str
    metrics: dict


class ResearchProvider(Protocol):
    async def screen_candidates(self, request: ScreenRequest) -> list[SignalDto]: ...
    async def analyze_symbol(self, symbol: str) -> ResearchReport: ...
