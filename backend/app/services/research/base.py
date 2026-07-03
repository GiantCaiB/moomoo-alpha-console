from dataclasses import dataclass
from typing import Protocol


@dataclass
class ScreenRequest:
    universe: list[str]
    max_results: int = 10
    min_score: float = 75.0


@dataclass
class SignalDto:
    symbol: str
    verdict: str  # BUY_STARTER, WATCH, AVOID
    total_score: float
    scores: list[dict]  # [{category, score, max_score, details}]
    reason: str
    entry_min: float | None
    entry_max: float | None
    stop_level: float | None
    target_size_pct: float | None
    risk_amount: float | None
    invalidation: str | None
    current_price: float | None


@dataclass
class ResearchReport:
    symbol: str
    summary: str
    metrics: dict


class ResearchProvider(Protocol):
    async def screen_candidates(self, request: ScreenRequest) -> list[SignalDto]: ...
    async def analyze_symbol(self, symbol: str) -> ResearchReport: ...
