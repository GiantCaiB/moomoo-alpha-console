from pydantic import BaseModel


class PositionResponse(BaseModel):
    id: str
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float | None
    unrealized_pnl: float | None
    day_pnl: float | None
    stop_level: float | None
    position_pct: float | None
    status: str
