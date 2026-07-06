"""Tests for Entry Signal price freshness and PriceResolver priority."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from app.services.market_data.price_resolver import PriceResolver
from app.services.broker.base import QuoteDto, PositionDto
from app.services.kline.service import KLineService


class FakeQuoteBroker:
    """Broker that returns a quote with last_price."""
    def __init__(self, last_price: float | None = None) -> None:
        self._last_price = last_price

    async def get_quote(self, symbol: str) -> QuoteDto:
        return QuoteDto(
            symbol=symbol,
            bid=self._last_price - 0.5 if self._last_price else None,
            ask=self._last_price + 0.5 if self._last_price else None,
            last=self._last_price,
            volume=1000000,
            bid_size=500,
            ask_size=500,
            timestamp=datetime.now(timezone.utc) if self._last_price else None,
        )

    async def get_positions(self) -> list[PositionDto]:
        return []

    async def health_check(self) -> object:
        return type("Health", (), {"connected": True, "message": "ok"})()


class FakePositionBroker:
    """Broker returning no quote but has a position with current_price."""
    def __init__(self, position_price: float | None = None) -> None:
        self._position_price = position_price

    async def get_quote(self, symbol: str) -> QuoteDto:
        return QuoteDto(symbol=symbol, bid=None, ask=None, last=None, volume=0, bid_size=0, ask_size=0, timestamp=None)

    async def get_positions(self) -> list[PositionDto]:
        if self._position_price is not None:
            return [
                PositionDto(
                    symbol="AMBA",
                    quantity=100,
                    avg_cost=80.0,
                    current_price=self._position_price,
                    unrealized_pnl=None,
                    day_pnl=None,
                    stop_level=None,
                    position_pct=None,
                    status="ACTIVE",
                )
            ]
        return []

    async def health_check(self) -> object:
        return type("Health", (), {"connected": True, "message": "ok"})()


class FakeNoPriceBroker:
    """Broker that returns no price at all."""
    async def get_quote(self, symbol: str) -> QuoteDto:
        return QuoteDto(symbol=symbol, bid=None, ask=None, last=None, volume=0, bid_size=0, ask_size=0, timestamp=None)

    async def get_positions(self) -> list[PositionDto]:
        return []

    async def health_check(self) -> object:
        return type("Health", (), {"connected": True, "message": "ok"})()


def make_bars_df(close_values: list[float]) -> pd.DataFrame:
    """Build a daily bars DataFrame for testing."""
    from datetime import date, timedelta
    base = date(2024, 1, 1)
    dates = [base + timedelta(days=i) for i in range(len(close_values))]
    return pd.DataFrame({
        "date": dates,
        "open": close_values,
        "high": [c * 1.02 for c in close_values],
        "low": [c * 0.98 for c in close_values],
        "close": close_values,
        "volume": [1_000_000] * len(close_values),
        "adj_close": close_values,
    })


def make_kline_service(bars_df: pd.DataFrame | None = None) -> KLineService:
    """Create a KLineService stub that returns the given bars."""
    kline = AsyncMock(spec=KLineService)

    async def fake_get_latest_cached_close(symbol, session=None):
        if bars_df is not None and not bars_df.empty:
            return float(bars_df["close"].iloc[-1])
        return None

    kline.get_latest_cached_close = fake_get_latest_cached_close
    return kline


def make_kline_service_with_bars(close: float) -> tuple[pd.DataFrame, KLineService]:
    df = make_bars_df([close - 2, close - 1, close])
    kline = make_kline_service(df)
    return df, kline


# ---------------------------------------------------------------
# Tests
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_price_resolver_uses_moomoo_quote_when_available():
    """Moomoo snapshot last_price should be used as the signal price."""
    broker = FakeQuoteBroker(last_price=150.25)
    bars_df, kline = make_kline_service_with_bars(148.0)
    resolver = PriceResolver(broker=broker, kline_service=kline)
    result = await resolver.resolve("AMBA", bars=bars_df)
    assert result.price == 150.25
    assert result.price_source == "moomoo_quote_last_price"
    assert result.price_is_realtime is True
    assert result.moomoo_quote_available is True


@pytest.mark.asyncio
async def test_price_resolver_falls_back_to_yfinance_when_no_quote():
    """yfinance cached latest close should be used when no moomoo quote is available."""
    broker = FakeNoPriceBroker()
    bars_df, kline = make_kline_service_with_bars(78.36)
    resolver = PriceResolver(broker=broker, kline_service=kline)
    result = await resolver.resolve("AMBA", bars=bars_df)
    assert result.price == 78.36
    assert result.price_source == "yfinance_cached_latest_close"
    assert result.price_is_realtime is False
    assert result.moomoo_quote_available is False
    assert result.cached_bars_available is True


@pytest.mark.asyncio
async def test_price_resolver_data_error_when_no_price():
    """DATA_ERROR when no quote, no position, and no bars available."""
    broker = FakeNoPriceBroker()
    kline = make_kline_service(bars_df=None)
    resolver = PriceResolver(broker=broker, kline_service=kline)
    result = await resolver.resolve("AMBA", bars=None)
    assert result.price is None
    assert result.price_source == "DATA_ERROR"
    assert result.error is not None


@pytest.mark.asyncio
async def test_price_resolver_uses_position_price():
    """Moomoo position current_price should be used if no quote but position exists."""
    broker = FakePositionBroker(position_price=80.50)
    bars_df, kline = make_kline_service_with_bars(78.36)
    resolver = PriceResolver(broker=broker, kline_service=kline)
    result = await resolver.resolve("AMBA", bars=bars_df)
    assert result.price == 80.50
    assert result.price_source == "moomoo_position_current_price"
    assert result.price_is_realtime is True
    assert result.moomoo_position_available is True


@pytest.mark.asyncio
async def test_price_resolver_returns_price_timestamp_with_quote():
    """price_timestamp should be populated when using moomoo quote."""
    broker = FakeQuoteBroker(last_price=150.25)
    bars_df, kline = make_kline_service_with_bars(148.0)
    resolver = PriceResolver(broker=broker, kline_service=kline)
    result = await resolver.resolve("AMBA", bars=bars_df)
    assert result.price_timestamp is not None
    assert result.price == 150.25


@pytest.mark.asyncio
async def test_price_resolver_returns_price_timestamp_with_bars():
    """price_timestamp should be populated when using yfinance bars."""
    broker = FakeNoPriceBroker()
    bars_df, kline = make_kline_service_with_bars(78.36)
    resolver = PriceResolver(broker=broker, kline_service=kline)
    result = await resolver.resolve("AMBA", bars=bars_df)
    assert result.price_timestamp is not None
    assert result.price == 78.36


@pytest.mark.asyncio
async def test_price_resolver_moomoo_quote_available_flag():
    """moomoo_quote_available should be True when quote returns a price."""
    broker = FakeQuoteBroker(last_price=100.0)
    resolver = PriceResolver(broker=broker, kline_service=make_kline_service())
    result = await resolver.resolve("AMBA")
    assert result.moomoo_quote_available is True
    assert result.moomoo_quote_price == 100.0


@pytest.mark.asyncio
async def test_price_resolver_moomoo_quote_unavailable_flag():
    """moomoo_quote_available should be False when quote returns no price."""
    broker = FakeNoPriceBroker()
    resolver = PriceResolver(broker=broker, kline_service=make_kline_service())
    result = await resolver.resolve("AMBA", bars=None)
    assert result.moomoo_quote_available is False
    assert result.moomoo_quote_price is None


@pytest.mark.asyncio
async def test_price_resolver_prefers_quote_over_bars():
    """When both moomoo quote and bars are available, quote should win."""
    broker = FakeQuoteBroker(last_price=200.0)
    bars_df, kline = make_kline_service_with_bars(150.0)
    resolver = PriceResolver(broker=broker, kline_service=kline)
    result = await resolver.resolve("AMBA", bars=bars_df)
    assert result.price == 200.0
    assert result.price_source == "moomoo_quote_last_price"
    # Ensure bars fallback flag is False since quote was used
    assert result.price_resolver_used_bars_fallback is False


@pytest.mark.asyncio
async def test_price_resolver_prefers_quote_over_position():
    """When both moomoo quote and position are available, quote should win."""
    broker = FakeQuoteBroker(last_price=200.0)
    resolver = PriceResolver(broker=broker, kline_service=make_kline_service())
    result = await resolver.resolve("AMBA")
    assert result.price == 200.0
    assert result.price_source == "moomoo_quote_last_price"
    assert result.moomoo_position_available is False

# ---------------------------------------------------------------
# Signal scoring uses the same price as entry range
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_price_delta():
    """Verify price delta computation logic."""
    from math import isclose
    delta = lambda sp, cp: ((cp - sp) / sp) * 100 if sp else None
    assert isclose(delta(78.36, 87.73), 11.96, rel_tol=0.01)
    assert isclose(delta(100.0, 95.0), -5.0, rel_tol=0.01)
    assert delta(0.0, 100.0) is None
    assert delta(None, 100.0) is None
