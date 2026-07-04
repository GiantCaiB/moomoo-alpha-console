from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import init_db
from app.services.broker.base import QuoteDto, PositionDto
from app.services.market_data.price_resolver import PriceResolver
from app.services.research.moomoo_momentum import MoomooMomentumResearchProvider
from app.services.settings.trading_universe import TradingUniverseResolver
from app.services.research.base import ScreenRequest


class FakeBroker:
    def __init__(self, quote_last: float | None = None, position_last: float | None = None):
        self.quote_last = quote_last
        self.position_last = position_last

    async def get_quote(self, symbol: str) -> QuoteDto:
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=self.quote_last,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_positions(self) -> list[PositionDto]:
        if self.position_last is None:
            return []
        return [
            PositionDto(
                symbol="AAPL",
                quantity=10,
                avg_cost=100.0,
                current_price=self.position_last,
                unrealized_pnl=0.0,
                day_pnl=0.0,
                stop_level=None,
                position_pct=1.0,
            )
        ]


class FakeKLineService:
    def __init__(self, latest_close: float | None = None, bars: int = 260):
        self.latest_close = latest_close
        self.bars = bars
        self.history_calls = 0

    async def get_daily_bars(self, symbol: str, lookback_days: int | None = None, session=None):
        return (await self.get_cached_or_fetch_daily_bars(symbol, lookback_days=lookback_days, session=session)).bars

    async def get_cached_or_fetch_daily_bars(self, symbol: str, lookback_days: int | None = None, session=None):
        self.history_calls += 1
        if self.bars <= 0:
            return SimpleNamespace(
                bars=pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"]),
                fetch_attempted=True,
                fetch_failed=True,
                fetch_error="empty_result",
                latest_bar_from_current_fetch=None,
            )
        dates = pd.date_range("2024-01-01", periods=self.bars, freq="D")
        bars = pd.DataFrame(
            {
                "date": dates,
                "open": [100.0] * self.bars,
                "high": [101.0] * self.bars,
                "low": [99.0] * self.bars,
                "close": [100.0] * self.bars,
                "volume": [1_000_000] * self.bars,
                "adj_close": [100.0] * self.bars,
            }
        )
        return SimpleNamespace(
            bars=bars,
            fetch_attempted=True,
            fetch_failed=False,
            fetch_error=None,
            latest_bar_from_current_fetch=dates[-1].isoformat(),
        )

    async def get_latest_cached_close(self, symbol: str, session=None):
        return self.latest_close

    def get_status(self):
        return {"provider": "yfinance", "cache_enabled": True}


@pytest.fixture
def client(api_app):
    transport = ASGITransport(app=api_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_universe_resolver_returns_default_symbols(monkeypatch):
    monkeypatch.setattr(settings, "universe_symbols", ["AAPL", "MSFT"])
    await init_db()
    resolver = TradingUniverseResolver()
    from app.db.session import create_session_factory
    from sqlalchemy import delete as sa_delete
    from app.models.app_setting import AppSetting
    factory = create_session_factory()
    async with factory() as session:
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        await session.commit()
        state = await resolver.resolve(session)
    assert state.symbols == ["AAPL", "MSFT"]
    assert state.source == "default"


@pytest.mark.asyncio
async def test_invalid_universe_symbols_rejected(client):
    await init_db()
    resp = await client.put("/api/v1/settings/trading-universe", json={"symbols": ["AAPL", "MOOMOO"]})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_price_resolver_falls_back_to_cached_close():
    resolver = PriceResolver(FakeBroker(quote_last=None), FakeKLineService(latest_close=123.45))
    result = await resolver.resolve("AAPL")
    assert result.price == 123.45
    assert result.price_source == "yfinance_cached_latest_close"
    assert result.price_is_realtime is False


@pytest.mark.asyncio
async def test_price_resolver_uses_position_price_when_quote_missing():
    resolver = PriceResolver(FakeBroker(quote_last=None, position_last=111.25), FakeKLineService(latest_close=None))
    result = await resolver.resolve("AAPL")
    assert result.price == 111.25
    assert result.price_source == "moomoo_position_current_price"
    assert result.price_is_realtime is True


@pytest.mark.asyncio
async def test_price_resolver_uses_bars_fallback_when_quote_missing():
    kline = FakeKLineService(latest_close=None, bars=260)
    bars = await kline.get_daily_bars("AAPL")
    resolver = PriceResolver(FakeBroker(quote_last=None), kline)
    result = await resolver.resolve("AAPL", bars=bars)
    assert result.price == 100.0
    assert result.price_source == "yfinance_cached_latest_close"
    assert result.price_timestamp is not None
    assert result.price_resolver_used_bars_fallback is True


@pytest.mark.asyncio
async def test_moomoo_provider_uses_cached_close_and_not_mock_data():
    kline = FakeKLineService(latest_close=123.45)
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(FakeBroker(quote_last=None), kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    signals = await provider.screen_candidates(ScreenRequest(universe=["AAPL"], max_results=5))
    assert signals
    signal = signals[0]
    assert signal.verdict != "DATA_ERROR"
    assert signal.price_source == "yfinance_cached_latest_close"
    assert signal.bar_source == "yfinance_cached_daily_bars"


@pytest.mark.asyncio
async def test_data_error_only_when_price_and_bars_unavailable():
    kline = FakeKLineService(latest_close=None, bars=0)
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(FakeBroker(quote_last=None), kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    signals = await provider.screen_candidates(ScreenRequest(universe=["AAPL"], max_results=5))
    assert signals
    assert signals[0].verdict == "DATA_ERROR"


@pytest.mark.asyncio
async def test_provider_fetches_bars_before_price_resolution():
    kline = FakeKLineService(latest_close=None, bars=260)
    broker = FakeBroker(quote_last=None)
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker, kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    signals = await provider.screen_candidates(ScreenRequest(universe=["NVDA"], max_results=5))
    assert signals
    assert signals[0].verdict != "DATA_ERROR"
    assert kline.history_calls >= 2
    assert signals[0].price_source == "yfinance_cached_latest_close"


@pytest.mark.asyncio
async def test_runtime_status_reports_read_only_moomoo(client, monkeypatch):
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    resp = await client.get("/api/v1/runtime/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mock_enabled"] is False
    assert data["read_only"] is True
    assert data["signal_provider"] == "MoomooMomentumResearchProvider"
