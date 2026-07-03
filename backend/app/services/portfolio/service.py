import logging
from app.services.broker.base import BrokerAdapter

logger = logging.getLogger(__name__)


async def get_portfolio_summary(broker: BrokerAdapter) -> dict:
    account = await broker.get_account()
    positions = await broker.get_positions()
    open_orders = await broker.get_open_orders()

    return {
        "total_value": account.total_value,
        "cash": account.cash,
        "positions_value": account.positions_value,
        "day_pnl": account.day_pnl,
        "day_pnl_pct": account.day_pnl_pct,
        "total_pnl": account.total_pnl,
        "total_pnl_pct": account.total_pnl_pct,
        "drawdown_pct": account.drawdown_pct,
        "num_positions": len(positions),
        "num_open_orders": len(open_orders),
        "currency": account.currency,
    }
