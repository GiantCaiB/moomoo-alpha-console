from fastapi import APIRouter

from app.schemas.config import ConfigResponse
from app.core.config import settings
from app.services.settings.trading_universe import TradingUniverseResolver

router = APIRouter()
resolver = TradingUniverseResolver()


@router.get("/api/v1/config", response_model=ConfigResponse)
async def get_config():
    return ConfigResponse(
        broker_mode=settings.broker_mode,
        trading_enabled=settings.trading_enabled,
        opend_host=settings.opend_host,
        opend_port=settings.opend_port,
        max_position_pct=settings.max_position_pct,
        max_risk_per_trade_pct=settings.max_risk_per_trade_pct,
        daily_loss_limit_pct=settings.daily_loss_limit_pct,
        max_drawdown_soft_pct=settings.max_drawdown_soft_pct,
        max_drawdown_hard_pct=settings.max_drawdown_hard_pct,
        universe_symbols=resolver.get_default_symbols(),
        allowed_order_types=settings.allowed_order_types,
    )
