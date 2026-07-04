import pytest
from datetime import datetime, timezone

from app.core.config import settings
from app.services.broker.mock import MockBrokerAdapter
from app.services.risk.engine import RiskEngine, OrderCheckContext
from app.services.broker.base import AccountSummary, QuoteDto


@pytest.fixture
def broker():
    b = MockBrokerAdapter()
    return b


@pytest.fixture
def risk_engine(monkeypatch):
    monkeypatch.setattr(settings, "universe_symbols", ["AAPL"])
    return RiskEngine()


@pytest.fixture
def sample_quote():
    return QuoteDto(
        symbol="AAPL",
        bid=210.0,
        ask=210.5,
        last=210.25,
        volume=1000000,
        bid_size=500,
        ask_size=500,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_portfolio():
    return AccountSummary(
        total_value=100000.0,
        cash=50000.0,
        positions_value=50000.0,
        day_pnl=500.0,
        day_pnl_pct=0.5,
        total_pnl=3000.0,
        total_pnl_pct=3.0,
        drawdown_pct=2.0,
        buying_power=100000.0,
    )


def make_context(
    symbol="AAPL",
    side="BUY",
    order_type="LIMIT",
    quantity=20,
    limit_price=210.0,
    stop_level=200.0,
    kill_switch=False,
    broker_connected=True,
    daily_loss_pct=0.0,
    drawdown_pct=0.0,
    portfolio=None,
    quote=None,
    positions=None,
    open_orders=None,
):
    return OrderCheckContext(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        limit_price=limit_price,
        stop_level=stop_level,
        portfolio=portfolio,
        quote=quote,
        positions=positions or [],
        open_orders=open_orders or [],
        daily_loss_pct=daily_loss_pct,
        drawdown_pct=drawdown_pct,
        kill_switch_enabled=kill_switch,
        broker_connected=broker_connected,
        strategy_run_id=None,
    )


@pytest.fixture
def api_broker():
    return MockBrokerAdapter()


@pytest.fixture
def api_risk_engine():
    return RiskEngine()


@pytest.fixture
def api_market_data():
    """Mock market data provider for API tests that need runtime/status."""
    from app.services.market_data.moomoo import MoomooMarketDataProvider
    return MoomooMarketDataProvider()


@pytest.fixture
def api_kline_service():
    from app.services.kline.service import KLineService
    from app.services.kline.yfinance_provider import YFinanceKLineProvider

    class FakeYFinanceProvider:
        def get_daily_bars(self, symbol, start_date, end_date, adjusted=True):
            import pandas as pd
            from datetime import timedelta
            dates = []
            current = start_date
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
            return pd.DataFrame({
                "date": dates,
                "open": [100.0] * len(dates),
                "high": [105.0] * len(dates),
                "low": [95.0] * len(dates),
                "close": [102.0] * len(dates),
                "volume": [1_000_000] * len(dates),
                "adj_close": [102.0] * len(dates),
            })

    service = KLineService(provider=FakeYFinanceProvider(), enable_cache=False)
    return service


@pytest.fixture
def api_app(api_broker, api_risk_engine, api_market_data, api_kline_service):
    from app.main import app
    from app.api.dependencies import (
        set_broker,
        set_risk_engine,
        set_market_data,
        set_kline_service,
        set_runtime_state,
        set_trading_universe_resolver,
        set_price_resolver,
    )
    from app.services.runtime.state import RuntimeStateService
    from app.services.settings.trading_universe import TradingUniverseResolver
    from app.services.market_data.price_resolver import PriceResolver
    set_broker(api_broker)
    set_risk_engine(api_risk_engine)
    set_market_data(api_market_data)
    set_kline_service(api_kline_service)
    resolver = TradingUniverseResolver()
    set_trading_universe_resolver(resolver)
    set_price_resolver(PriceResolver(api_broker, api_kline_service))
    set_runtime_state(RuntimeStateService(api_broker, api_kline_service, resolver))
    return app
