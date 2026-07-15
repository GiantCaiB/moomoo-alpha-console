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
    strategy_name: str | None = None
    data_source: str | None = None
    generated_at: datetime | None = None
    universe: list[str] | None = None
    price_source: str | None = None
    price_as_of: str | None = None
    bar_source: str | None = None
    is_real_market_data: bool = False
    is_tradeable: bool = False
    has_error: bool = False
    failed_filters: list[str] | None = None
    data_quality_status: str = "OK"
    calculated_score_before_filters: float | None = None
    run_id: str | None = None


class EntrySignalRunResponse(BaseModel):
    id: str
    strategy_profile_id: str | None
    strategy_name: str
    strategy_version: str | None
    status: str
    symbols_scanned: int
    signals_generated: int
    data_error_count: int
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    parameters_snapshot_json: str | None
    created_at: datetime


class StaleSignalCountResponse(BaseModel):
    stale_count: int
    local_or_mock_count: int
    out_of_universe_count: int
    stale_symbols: list[str]
    local_or_mock_symbols: list[str]
    out_of_universe_symbols: list[str]
