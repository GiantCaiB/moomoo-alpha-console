from pydantic import BaseModel


class PortfolioSummary(BaseModel):
    total_value: float
    cash: float
    positions_value: float
    day_pnl: float
    day_pnl_pct: float
    total_pnl: float
    total_pnl_pct: float
    drawdown_pct: float
    num_positions: int
    num_open_orders: int
