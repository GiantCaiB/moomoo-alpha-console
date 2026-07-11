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


@pytest.mark.asyncio
async def test_high_score_with_hard_filter_exposes_reason():
    """AVOID with score >= 75 must expose hard filter reason in reason and failed_filters.

    Builds a strong uptrend (score >= 75) but with low final volume to trigger
    the volume_ratio_below_threshold hard filter.
    """
    provider = LocalMomentumResearchProvider()
    MOCK_BARS.clear()

    def build_bars(start: float, end: float, volume: int = 1_000_000) -> list[tuple]:
        bars: list[tuple] = []
        d = date(2024, 1, 1)
        count = 260
        for i in range(count):
            price = start + (end - start) * i / (count - 1)
            bars.append((d, price * 0.99, price * 1.02, price * 0.98, price, volume))
            d += timedelta(days=1)
        return bars

    MOCK_BARS["SPY"] = build_bars(100.0, 200.0, volume=5_000_000)

    # Strong uptrend (100 -> 195) gives good scores, but last bar has tiny volume
    MOCK_BARS["HIGH_SCORE"] = build_bars(100.0, 195.0, volume=5_000_000)
    MOCK_BARS["HIGH_SCORE"][-1] = (
        MOCK_BARS["HIGH_SCORE"][-1][0],
        MOCK_BARS["HIGH_SCORE"][-1][1],
        MOCK_BARS["HIGH_SCORE"][-1][2],
        MOCK_BARS["HIGH_SCORE"][-1][3],
        MOCK_BARS["HIGH_SCORE"][-1][4],
        100,  # extremely low volume on last bar to trigger volume hard filter
    )

    request = ScreenRequest(universe=["HIGH_SCORE"], max_results=5)
    signals = await provider.screen_candidates(request)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "AVOID", f"Expected AVOID, got {sig.verdict} (score={sig.total_score})"
    assert sig.total_score >= 75, f"Expected high score, got {sig.total_score}"
    assert sig.failed_filters is not None
    assert len(sig.failed_filters) > 0
    assert "volume_ratio_below_threshold" in sig.failed_filters, f"Expected volume hard filter, got {sig.failed_filters}"
    assert sig.calculated_score_before_filters is not None
    assert sig.calculated_score_before_filters >= 75
    assert "volume" in sig.reason.lower()
