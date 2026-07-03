from pydantic import BaseModel


class RiskStatusResponse(BaseModel):
    kill_switch_enabled: bool
    broker_connected: bool
    daily_loss_pct: float
    drawdown_pct: float
    daily_loss_limit_pct: float
    max_drawdown_soft_pct: float
    max_drawdown_hard_pct: float
    daily_loss_exceeded: bool
    drawdown_soft_exceeded: bool
    drawdown_hard_exceeded: bool
    recent_events: list[dict]
    trading_blocked: bool


class KillSwitchRequest(BaseModel):
    enabled: bool
