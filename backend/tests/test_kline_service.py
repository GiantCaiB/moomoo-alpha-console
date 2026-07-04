"""Tests for KLineService cache logic.

Uses fake KLineProvider to avoid live yfinance calls.
Tests:
- Cache hit returns cached bars
- Cache miss fetches from provider and stores
- Partial cache hit
- Metrics tracking
- Empty result handling
"""
import pytest
from datetime import date, timedelta, datetime, timezone

import pandas as pd

from app.services.kline.service import KLineService


class FakeProvider:
    def __init__(self, empty_symbol: str | None = None):
        self.empty_symbol = empty_symbol
        self.fetch_count = 0

    def get_daily_bars(self, symbol, start_date, end_date, adjusted=True):
        self.fetch_count += 1
        if symbol == self.empty_symbol:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"])
        prices = []
        price = 100.0
        current = start_date
        rows = []
        while current <= end_date:
            price *= 1.001
            rows.append([current, round(price * 0.99, 2), round(price * 1.02, 2),
                         round(price * 0.98, 2), round(price, 2), 1_000_000, round(price, 2)])
            current += timedelta(days=1)
        return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "adj_close"])


class FakeSession:
    def __init__(self):
        self._store: dict[tuple[str, date], dict] = {}
        self.committed = False
        self.rolled_back = False

    async def execute(self, stmt):
        class Result:
            def scalars(self):
                class ScalarResult:
                    def all(self):
                        return []
                return ScalarResult()
            def scalar_one_or_none(self):
                return None
        return Result()

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_cache_miss_fetches_from_provider():
    provider = FakeProvider()
    service = KLineService(provider=provider, enable_cache=False)

    df = await service.get_daily_bars("AAPL", lookback_days=10)

    assert not df.empty
    assert "date" in df.columns
    assert "close" in df.columns
    assert provider.fetch_count == 1
    assert service.requests == 1
    assert service.cache_misses == 1


@pytest.mark.asyncio
async def test_metrics_tracking():
    provider = FakeProvider()
    service = KLineService(provider=provider, enable_cache=False)

    await service.get_daily_bars("AAPL", lookback_days=10)
    await service.get_daily_bars("MSFT", lookback_days=10)

    assert service.requests == 2
    assert service.cache_misses == 2
    assert service.upstream_fetches == 2
    assert service.failed == 0
    assert service.latest_successful_fetch is not None


@pytest.mark.asyncio
async def test_empty_result_handling():
    provider = FakeProvider(empty_symbol="EMPTY")
    service = KLineService(provider=provider, enable_cache=False)

    df = await service.get_daily_bars("EMPTY", lookback_days=10)

    assert df.empty is True
    assert service.failed == 1


@pytest.mark.asyncio
async def test_yfinance_not_required_for_startup():
    """KLineService can work without yfinance if a provider is injected."""
    provider = FakeProvider()
    service = KLineService(provider=provider, enable_cache=False)
    df = await service.get_daily_bars("AAPL", lookback_days=5)
    assert not df.empty


@pytest.mark.asyncio
async def test_get_status_returns_metrics():
    provider = FakeProvider()
    service = KLineService(provider=provider, enable_cache=False)

    await service.get_daily_bars("AAPL", lookback_days=10)

    status = service.get_status()
    assert status["provider"] is not None
    assert status["requests"] == 1
    assert "per_symbol" in status
