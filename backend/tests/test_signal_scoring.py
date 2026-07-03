"""Tests for the momentum relative strength signal scoring."""
import pytest
from app.services.research.local_momentum import LocalMomentumResearchProvider
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
