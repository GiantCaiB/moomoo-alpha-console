"""Tests for the momentum relative strength signal scoring."""
from datetime import date, timedelta

import pytest
from app.services.research.local_momentum import LocalMomentumResearchProvider, MOCK_BARS
from app.services.research.base import ScreenRequest


@pytest.mark.asyncio
async def test_screener_returns_signals():
    provider = LocalMomentumResearchProvider()
    request = ScreenRequest(universe=["AAPL", "MSFT", "NVDA"], max_results=5)
    signals = await provider.screen_candidates(request)
    assert len(signals) > 0
    for sig in signals:
        assert sig.symbol in ["AAPL", "MSFT", "NVDA"]
        assert sig.verdict in ("BUY_STARTER", "WATCH", "AVOID")
        assert sig.total_score >= 0
        assert sig.total_score <= 100


@pytest.mark.asyncio
async def test_screener_verdict_types():
    provider = LocalMomentumResearchProvider()
    request = ScreenRequest(universe=["SPY", "QQQ", "AAPL"], max_results=10)
    signals = await provider.screen_candidates(request)
    verdicts = {s.verdict for s in signals}
    assert verdicts.issubset({"BUY_STARTER", "WATCH", "AVOID"})


@pytest.mark.asyncio
async def test_buy_starter_has_entry_range():
    provider = LocalMomentumResearchProvider()
    request = ScreenRequest(universe=["AAPL", "MSFT", "NVDA"], max_results=10)
    signals = await provider.screen_candidates(request)
    buy_signals = [s for s in signals if s.verdict == "BUY_STARTER" and s.total_score >= 75]
    for sig in buy_signals:
        assert sig.entry_min is not None
        assert sig.entry_max is not None
        assert sig.stop_level is not None
        assert sig.target_size_pct is not None
        assert sig.risk_amount is not None


@pytest.mark.asyncio
async def test_signal_labels_mock_data():
    provider = LocalMomentumResearchProvider()
    request = ScreenRequest(universe=["AAPL", "MSFT"])
    signals = await provider.screen_candidates(request)
    assert len(signals) > 0
    for sig in signals:
        assert sig.is_real_market_data is False
        assert sig.is_tradeable is False
        assert sig.data_source == "local_generated"
        assert sig.price_source == "mock_synthetic"
        assert sig.bar_source == "mock_generated"
        assert sig.strategy_name == "momentum_relative_strength"
        assert sig.universe == ["AAPL", "MSFT"]
        assert sig.generated_at is not None


@pytest.mark.asyncio
async def test_hard_filter_failure_keeps_computed_score_and_breakdown():
    provider = LocalMomentumResearchProvider()
    MOCK_BARS.clear()

    def build_bars(close: float, volume: int = 1_000_000) -> list[tuple]:
        bars: list[tuple] = []
        d = date(2024, 1, 1)
        price = close
        for _ in range(260):
            bars.append((d, price, price + 1, price - 1, price, volume))
            d += timedelta(days=1)
        return bars

    MOCK_BARS["SPY"] = build_bars(100.0)
    MOCK_BARS["AAPL"] = build_bars(90.0)

    request = ScreenRequest(universe=["AAPL"], max_results=5)
    signals = await provider.screen_candidates(request)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "AVOID"
    assert sig.total_score > 0
    assert sig.scores
    assert sig.failed_filters
    assert sig.data_quality_status == "OK"
    assert sig.calculated_score_before_filters == sig.total_score
