from datetime import datetime

from pydantic import BaseModel


class PositionManagementSignalResponse(BaseModel):
    id: str | None = None
    symbol: str
    signal: str
    reason: str | None
    current_price: float | None
    avg_cost: float | None
    quantity: int | None
    gain_pct: float | None
    suggested_action: str | None
    suggested_quantity: int | None
    suggested_trim_pct: float | None
    tail_mode: bool
    weekly_close: float | None
    weekly_sma20: float | None
    weekly_sma30: float | None
    drawdown_from_high: float | None
    original_cost_basis: float | None = None
    highest_price_since_entry: float | None = None
    tail_started_at: datetime | None = None
    trim_25_done: bool | None = None
    trim_50_done: bool | None = None
    trim_75_done: bool | None = None
    data_source: str | None
    price_source: str | None
    bar_source: str | None
    is_real_market_data: bool
    generated_at: datetime
    created_at: datetime


class PositionSignalRunResponse(BaseModel):
    status: str
    positions_scanned: int
    signals_generated: int
    data_error_count: int
    read_only: bool
    error: str | None = None
