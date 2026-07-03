from pydantic import BaseModel


class ConfigResponse(BaseModel):
    broker_mode: str
    trading_enabled: bool
    opend_host: str
    opend_port: int
    max_position_pct: float
    max_risk_per_trade_pct: float
    daily_loss_limit_pct: float
    max_drawdown_soft_pct: float
    max_drawdown_hard_pct: float
    universe_symbols: list[str]
    allowed_order_types: list[str]
