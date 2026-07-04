"""
Moomoo Alpha Console — FastAPI Application

Entry point for the backend server.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import init_db, close_engine
from app.services.broker.mock import MockBrokerAdapter
from app.services.broker.paper import PaperBrokerAdapter
from app.services.broker.moomoo import MoomooBrokerAdapter
from app.services.risk.engine import RiskEngine
from app.api.dependencies import (
    set_broker,
    set_risk_engine,
    set_market_data,
    set_kline_service,
    set_runtime_state,
    set_trading_universe_resolver,
    set_price_resolver,
)
from app.services.market_data.moomoo import MoomooMarketDataProvider
from app.services.kline.yfinance_provider import YFinanceKLineProvider
from app.services.kline.service import KLineService
from app.services.settings.trading_universe import TradingUniverseResolver
from app.services.market_data.price_resolver import PriceResolver
from app.services.runtime.state import RuntimeStateService
from app.api import (
    health_router,
    config_router,
    portfolio_router,
    positions_router,
    orders_router,
    signals_router,
    position_signals_router,
    risk_router,
    watchlist_router,
    settings_router,
    runtime_router,
    diagnostics_router,
    market_data_router,
    ws_router,
)
from app.workers.scheduler import setup_scheduler, start_scheduler, stop_scheduler

setup_logging()
logger = logging.getLogger(__name__)


def create_broker():
    mode = settings.broker_mode.lower()
    if mode == "moomoo":
        return MoomooBrokerAdapter()
    elif mode == "paper":
        return PaperBrokerAdapter()
    else:
        return MockBrokerAdapter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Moomoo Alpha Console (broker_mode=%s)", settings.broker_mode)

    await init_db()

    broker = create_broker()
    await broker.connect()
    set_broker(broker)
    logger.info("Broker initialized: %s", type(broker).__name__)

    if settings.broker_mode.lower() == "moomoo":
        md_provider = MoomooMarketDataProvider()
        logger.info("Market data provider: MoomooMarketDataProvider")
    else:
        md_provider = MoomooMarketDataProvider()
        logger.info("Market data provider: MoomooMarketDataProvider (SDK may be unavailable in mock mode)")
    set_market_data(md_provider)

    enable_cache = settings.enable_kline_cache
    provider_type = settings.kline_provider
    logger.info("KLine provider: %s (cache=%s, lookback=%dd)", provider_type, enable_cache, settings.kline_lookback_days)

    if provider_type == "yfinance":
        yf_provider = YFinanceKLineProvider()
        kline_service = KLineService(provider=yf_provider, enable_cache=enable_cache)
    else:
        raise RuntimeError(f"Unknown kline_provider: {provider_type}")

    set_kline_service(kline_service)
    trading_universe_resolver = TradingUniverseResolver()
    set_trading_universe_resolver(trading_universe_resolver)
    price_resolver = PriceResolver(broker=broker, kline_service=kline_service)
    set_price_resolver(price_resolver)
    runtime_state = RuntimeStateService(
        broker=broker,
        kline_service=kline_service,
        trading_universe_resolver=trading_universe_resolver,
    )
    set_runtime_state(runtime_state)

    risk_engine = RiskEngine()
    set_risk_engine(risk_engine)

    setup_scheduler()
    start_scheduler()

    yield

    stop_scheduler()
    await broker.disconnect()
    await close_engine()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(config_router)
app.include_router(portfolio_router)
app.include_router(positions_router)
app.include_router(orders_router)
app.include_router(signals_router)
app.include_router(position_signals_router)
app.include_router(risk_router)
app.include_router(watchlist_router)
app.include_router(settings_router)
app.include_router(runtime_router)
app.include_router(diagnostics_router)
app.include_router(market_data_router)
app.include_router(ws_router)
