from app.api.routes.health import router as health_router
from app.api.routes.config import router as config_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.positions import router as positions_router
from app.api.routes.orders import router as orders_router
from app.api.routes.signals import router as signals_router
from app.api.routes.position_signals import router as position_signals_router
from app.api.routes.risk import router as risk_router
from app.api.routes.watchlist import router as watchlist_router
from app.api.routes.settings import router as settings_router
from app.api.routes.runtime import router as runtime_router
from app.api.routes.diagnostics import router as diagnostics_router
from app.api.routes.market_data import router as market_data_router
from app.api.websocket import router as ws_router

__all__ = [
    "health_router",
    "config_router",
    "portfolio_router",
    "positions_router",
    "orders_router",
    "signals_router",
    "position_signals_router",
    "risk_router",
    "watchlist_router",
    "settings_router",
    "runtime_router",
    "diagnostics_router",
    "market_data_router",
    "ws_router",
]
