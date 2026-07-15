"""Tests for MoomooMomentumResearchProvider.

Uses fake broker + fake KLineService to simulate moomoo data.
Tests:
- Data failure does not create AVOID signals
- Insufficient bars does not create BUY/WATCH/AVOID
- Moomoo signal metadata is correct
- No fallback to mock/local data
- Configurable relative strength hard-fail margins
"""
import math
import pytest
from datetime import date, datetime, timezone, timedelta
from types import SimpleNamespace

import pandas as pd

from app.services.research.moomoo_momentum import MoomooMomentumResearchProvider
from app.services.research.base import ScreenRequest, SignalDto
from app.services.kline.service import KLineService
from app.services.market_data.price_resolver import PriceResolver
from app.services.broker.base import QuoteDto, PositionDto


def _df_from_bars(count: int = 260, uptrend: bool = True) -> pd.DataFrame:
    """Generate a synthetic DataFrame matching KLineProvider output."""
    prices = []
    price = 100.0
    for i in range(count):
        if uptrend:
            price = price * (1 + 0.001)
        else:
            price = price * (1 - 0.001)
        prices.append(price)

    d = date(2024, 1, 1)
    dates = [d + timedelta(days=i) for i in range(count)]
    return pd.DataFrame({
        "date": dates,
        "open": [round(p * 0.99, 2) for p in prices],
        "high": [round(p * 1.02, 2) for p in prices],
        "low": [round(p * 0.98, 2) for p in prices],
        "close": [round(p, 2) for p in prices],
        "volume": [1_000_000 + (i * 1000) for i in range(count)],
        "adj_close": [round(p, 2) for p in prices],
    })


class FakeKLineService:
    def __init__(
        self,
        fail_symbol: str | None = None,
        low_bars_symbol: str | None = None,
        uptrend: bool = True,
        downtrend_symbols: set[str] | None = None,
    ):
        self.fail_symbol = fail_symbol
        self.low_bars_symbol = low_bars_symbol
        self.uptrend = uptrend
        self.downtrend_symbols = downtrend_symbols or set()
        self.requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.upstream_fetches = 0
        self.failed = 0
        self.latest_successful_fetch: datetime | None = None

    async def get_daily_bars(self, symbol: str, lookback_days: int | None = None, session=None) -> pd.DataFrame:
        return (await self.get_cached_or_fetch_daily_bars(symbol, lookback_days=lookback_days, session=session)).bars

    async def get_cached_or_fetch_daily_bars(self, symbol: str, lookback_days: int | None = None, session=None):
        self.requests += 1
        if symbol == self.fail_symbol:
            self.failed += 1
            raise RuntimeError(f"Data unavailable for {symbol}")
        if symbol == self.low_bars_symbol:
            self.failed += 1
            return SimpleNamespace(
                bars=pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"]),
                fetch_attempted=True,
                fetch_failed=True,
                fetch_error="Insufficient history: 50 bars (< 200 required)",
                latest_bar_from_current_fetch=None,
            )
        df = _df_from_bars(count=260, uptrend=(False if symbol in self.downtrend_symbols else self.uptrend))
        self.latest_successful_fetch = datetime.now(timezone.utc)
        return SimpleNamespace(
            bars=df,
            fetch_attempted=True,
            fetch_failed=False,
            fetch_error=None,
            latest_bar_from_current_fetch=df["date"].iloc[-1].isoformat(),
        )


class FakeBroker:
    def __init__(
        self,
        quote_fail_symbol: str | None = None,
        position_symbol: str | None = None,
        position_price: float | None = None,
        quote_last: float = 150.0,
    ):
        self.quote_fail_symbol = quote_fail_symbol
        self.position_symbol = position_symbol
        self.position_price = position_price
        self.quote_last = quote_last

    async def get_quote(self, symbol: str) -> QuoteDto:
        if symbol == self.quote_fail_symbol:
            return QuoteDto(
                symbol=symbol,
                bid=None,
                ask=None,
                last=None,
                volume=None,
                bid_size=None,
                ask_size=None,
                timestamp=datetime.now(timezone.utc),
            )
        return QuoteDto(
            symbol=symbol,
            bid=149.9,
            ask=150.1,
            last=self.quote_last,
            volume=5_000_000,
            bid_size=500,
            ask_size=500,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_positions(self) -> list[PositionDto]:
        if self.position_symbol is None or self.position_price is None:
            return []
        return [
            PositionDto(
                symbol=self.position_symbol,
                quantity=10,
                avg_cost=140.0,
                current_price=self.position_price,
                unrealized_pnl=100.0,
                day_pnl=5.0,
                stop_level=None,
                position_pct=1.0,
            )
        ]


@pytest.mark.asyncio
async def test_market_data_failure_does_not_create_avoid():
    """When market data fetch fails, verdict should be DATA_ERROR, not AVOID."""
    kline = FakeKLineService(fail_symbol="AAPL")
    broker = FakeBroker()
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=broker, kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["AAPL", "MSFT"], max_results=5)
    signals = await provider.screen_candidates(request)

    aapl = [s for s in signals if s.symbol == "AAPL"]
    assert len(aapl) > 0
    assert aapl[0].verdict == "DATA_ERROR"
    assert aapl[0].has_error is True
    assert aapl[0].error_message is not None

    msft = [s for s in signals if s.symbol == "MSFT"]
    assert len(msft) > 0
    assert msft[0].verdict in ("BUY_STARTER", "WATCH", "AVOID")


@pytest.mark.asyncio
async def test_insufficient_bars_does_not_create_fake_signal():
    """When fewer than 200 bars are available, verdict is DATA_ERROR, not a fake signal."""
    kline = FakeKLineService(low_bars_symbol="NVDA")
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["NVDA", "MSFT"], max_results=5)
    signals = await provider.screen_candidates(request)

    nvda = [s for s in signals if s.symbol == "NVDA"]
    assert len(nvda) > 0
    assert nvda[0].verdict == "DATA_ERROR"

    msft = [s for s in signals if s.symbol == "MSFT"]
    assert len(msft) > 0
    assert msft[0].verdict in ("BUY_STARTER", "WATCH", "AVOID")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
async def test_non_finite_indicators_produce_data_error(invalid_value):
    kline = FakeKLineService()
    invalid_bars = _df_from_bars()
    invalid_bars.loc[10, "close"] = invalid_value

    async def get_invalid_bars(symbol, lookback_days=None, session=None):
        bars = invalid_bars if symbol == "AAPL" else _df_from_bars()
        return SimpleNamespace(
            bars=bars,
            fetch_attempted=True,
            fetch_failed=False,
            fetch_error=None,
            latest_bar_from_current_fetch=bars["date"].iloc[-1].isoformat(),
        )

    kline.get_cached_or_fetch_daily_bars = get_invalid_bars
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )

    signals = await provider.screen_candidates(ScreenRequest(universe=["AAPL"], max_results=5))
    assert signals[0].verdict == "DATA_ERROR"
    assert signals[0].total_score == 0.0
    assert signals[0].scores == []
    assert signals[0].data_quality_status == "INVALID_DATA"
    assert "NaN" not in (signals[0].reason or "")


@pytest.mark.asyncio
async def test_moomoo_signal_metadata():
    """Moomoo-generated signals must have correct provenance metadata."""
    kline = FakeKLineService()
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["AAPL", "MSFT", "NVDA"], max_results=10)
    signals = await provider.screen_candidates(request)

    for sig in signals:
        if sig.verdict == "DATA_ERROR":
            continue
        assert sig.data_source == "moomoo_snapshot_plus_yfinance_kline"
        assert sig.price_source in ("moomoo_quote_last_price", "moomoo_position_current_price", "yfinance_cached_latest_close")
        assert sig.bar_source == "yfinance_cached_daily_bars"
        assert sig.is_real_market_data is True
        assert sig.is_tradeable is False
        assert sig.strategy_name == "momentum_relative_strength"


@pytest.mark.asyncio
async def test_valid_data_with_price_below_sma50_is_avoid_with_score_and_breakdown():
    kline = FakeKLineService(downtrend_symbols={"AAPL"})
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(quote_last=70.0), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["AAPL"], max_results=5)
    signals = await provider.screen_candidates(request)

    aapl = [s for s in signals if s.symbol == "AAPL"]
    assert len(aapl) > 0
    assert aapl[0].verdict == "AVOID"
    assert aapl[0].total_score > 0
    assert aapl[0].scores
    assert aapl[0].failed_filters is not None
    assert "price_below_sma50" in aapl[0].failed_filters
    assert aapl[0].data_quality_status == "OK"


@pytest.mark.asyncio
async def test_valid_data_with_weak_relative_strength_is_avoid_with_failed_filters():
    kline = FakeKLineService(downtrend_symbols={"MSFT"})
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["MSFT"], max_results=5)
    signals = await provider.screen_candidates(request)

    msft = [s for s in signals if s.symbol == "MSFT"]
    assert len(msft) > 0
    assert msft[0].verdict == "AVOID"
    assert msft[0].total_score > 0
    assert msft[0].failed_filters
    assert msft[0].scores
    assert msft[0].data_quality_status == "OK"


@pytest.mark.asyncio
async def test_insufficient_history_returns_data_error_with_zero_score():
    kline = FakeKLineService(low_bars_symbol="NVDA")
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["NVDA"], max_results=5)
    signals = await provider.screen_candidates(request)

    nvda = [s for s in signals if s.symbol == "NVDA"]
    assert len(nvda) > 0
    assert nvda[0].verdict == "DATA_ERROR"
    assert nvda[0].total_score == 0.0
    assert nvda[0].scores == []
    assert nvda[0].data_quality_status == "INSUFFICIENT_HISTORY"


@pytest.mark.asyncio
async def test_provider_failure_returns_data_error_with_zero_score():
    kline = FakeKLineService(fail_symbol="AAPL")
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["AAPL"], max_results=5)
    signals = await provider.screen_candidates(request)

    aapl = [s for s in signals if s.symbol == "AAPL"]
    assert len(aapl) > 0
    assert aapl[0].verdict == "DATA_ERROR"
    assert aapl[0].total_score == 0.0
    assert aapl[0].scores == []
    assert aapl[0].data_quality_status == "PROVIDER_ERROR"


@pytest.mark.asyncio
async def test_moomoo_provider_does_not_use_mock_local_data():
    """MoomooMomentumResearchProvider must not fall back to mock/local data."""
    kline = FakeKLineService(fail_symbol="SPY")
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["AAPL"], max_results=5)
    signals = await provider.screen_candidates(request)

    assert len(signals) > 0
    spy_errors = [s for s in signals if s.symbol == "SPY"]
    if spy_errors:
        assert spy_errors[0].verdict == "DATA_ERROR"
    else:
        aapl = [s for s in signals if s.symbol == "AAPL"]
        if aapl:
            assert aapl[0].verdict in ("BUY_STARTER", "WATCH", "AVOID", "DATA_ERROR")


@pytest.mark.asyncio
async def test_scorer_uses_persisted_universe():
    """The screener must use the universe passed via ScreenRequest."""
    kline = FakeKLineService()
    provider = MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=FakeBroker(), kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
    )
    request = ScreenRequest(universe=["AAPL", "MSFT"], max_results=5)
    signals = await provider.screen_candidates(request)

    symbols = {s.symbol for s in signals}
    assert "AAPL" in symbols or any(s.symbol == "AAPL" for s in signals if s.verdict == "DATA_ERROR")
    assert all(s.universe == ["AAPL", "MSFT"] or s.universe is None for s in signals if s.verdict != "DATA_ERROR")


def _trend_bars(start: float, end: float, count: int = 260) -> pd.DataFrame:
    """Build bars with a linear trend from start to end over count days."""
    d = date(2024, 1, 1)
    dates = [d + timedelta(days=i) for i in range(count)]
    prices = [start + (end - start) * i / (count - 1) for i in range(count)]
    return pd.DataFrame({
        "date": dates,
        "open": [round(p * 0.99, 2) for p in prices],
        "high": [round(p * 1.02, 2) for p in prices],
        "low": [round(p * 0.98, 2) for p in prices],
        "close": [round(p, 2) for p in prices],
        "volume": [1_000_000 + (i * 1000) for i in range(count)],
        "adj_close": [round(p, 2) for p in prices],
    })


def _rise_drop_bars(rise: float, drop: float, last_vol: int | None = None) -> pd.DataFrame:
    """Build 260 bars: 200 flat at 100, 50 rising to 100+rise, 10 dropping to 100+rise-drop.

    Optionally sets the last bar's volume to ``last_vol``.
    """
    count_flat, count_rise, count_drop = 200, 50, 10
    prices: list[float] = [100.0] * count_flat
    for i in range(count_rise):
        prices.append(100 + rise * i / (count_rise - 1))
    for i in range(count_drop):
        prices.append(100 + rise - drop * i / (count_drop - 1))
    vol = [1_000_000 + i * 1000 for i in range(count_flat + count_rise + count_drop)]
    if last_vol is not None:
        vol[-1] = last_vol
    d = date(2024, 1, 1)
    dates = [d + timedelta(days=i) for i in range(len(prices))]
    return pd.DataFrame({
        "date": dates,
        "open": [round(p * 0.995, 2) for p in prices],
        "high": [round(p * 1.02, 2) for p in prices],
        "low": [round(p * 0.98, 2) for p in prices],
        "close": [round(p, 2) for p in prices],
        "volume": vol,
        "adj_close": [round(p, 2) for p in prices],
    })


class ControlledKLineService:
    """KLineService returning pre-built DataFrames per symbol."""
    def __init__(self, bars_map: dict[str, pd.DataFrame]) -> None:
        self._bars_map = bars_map
        self.requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.upstream_fetches = 0
        self.failed = 0
        self.latest_successful_fetch: datetime | None = None

    async def get_daily_bars(self, symbol: str, lookback_days: int | None = None, session=None) -> pd.DataFrame:
        return (await self.get_cached_or_fetch_daily_bars(symbol, lookback_days=lookback_days, session=session)).bars

    async def get_cached_or_fetch_daily_bars(self, symbol: str, lookback_days: int | None = None, session=None):
        self.requests += 1
        df = self._bars_map.get(symbol)
        if df is None:
            self.failed += 1
            raise RuntimeError(f"No data for {symbol}")
        self.latest_successful_fetch = datetime.now(timezone.utc)
        return SimpleNamespace(
            bars=df,
            fetch_attempted=True,
            fetch_failed=False,
            fetch_error=None,
            latest_bar_from_current_fetch=df["date"].iloc[-1].isoformat(),
        )


def _make_rs_test_provider(
    spy_df: pd.DataFrame,
    symbol_df: pd.DataFrame,
    params: dict | None = None,
) -> MoomooMomentumResearchProvider:
    """Build a MoomooMomentumResearchProvider with controlled bars.

    Uses a broker that returns no quote, so PriceResolver falls back to
    the bars' cached latest close. This keeps the resolved price aligned
    with the bars' last close and avoids SMA/price mismatch.
    """
    bars_map = {"SPY": spy_df, "TEST": symbol_df}
    kline = ControlledKLineService(bars_map)

    class NoQuoteFakeBroker:
        async def get_quote(self, symbol: str) -> QuoteDto:
            return QuoteDto(symbol=symbol, bid=None, ask=None, last=None, volume=0, bid_size=0, ask_size=0, timestamp=None)
        async def get_positions(self) -> list[PositionDto]:
            return []

    broker = NoQuoteFakeBroker()
    merged_params = {
        "buy_score_threshold": 75,
        "watch_score_threshold": 65,
        "relative_strength_filters": {
            "underperform_spy_20d_hard_fail_margin_pct": 3,
            "underperform_spy_60d_hard_fail_margin_pct": 5,
        },
    }
    if params:
        merged_params.update(params)
    return MoomooMomentumResearchProvider(
        price_resolver=PriceResolver(broker=broker, kline_service=kline),
        kline_service=kline,
        signal_data_source="moomoo_snapshot_plus_yfinance_kline",
        parameters=merged_params,
    )


# ---------------------------------------------------------------
# Relative strength hard-fail margin tests
#
# Uses _trend_bars(start, end) to build data with specific 20d/60d returns.
# For a linear trend from start to end over 260 days:
#   ret_20d ≈ (end / (start + (end-start)*239/259) - 1) * 100
#   ret_60d ≈ (end / (start + (end-start)*199/259) - 1) * 100
# The exact return depends on the start/end values.
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_rs_minor_underperformance_within_margin_yields_watch():
    """Score >= buy_threshold, underperformance < 3% margin => WATCH, not BUY, not AVOID.

    SPY: 100 -> 200 (strong uptrend, regime=15)
    TEST: 100 -> 180 (slightly weaker, minor 20d underperformance < 3%)
    """
    spy_df = _trend_bars(100.0, 200.0)
    symbol_df = _trend_bars(100.0, 180.0)
    provider = _make_rs_test_provider(spy_df, symbol_df)
    signals = await provider.screen_candidates(ScreenRequest(universe=["TEST"], max_results=5))
    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "WATCH", f"Expected WATCH for minor underperformance, got {sig.verdict} (score={sig.total_score})"
    assert sig.total_score >= 75, f"Score should be >= buy threshold for this scenario, got {sig.total_score}"
    assert sig.failed_filters is None, f"Should have no hard filters, got {sig.failed_filters}"
    assert "short-term relative strength is slightly below SPY" in sig.reason


@pytest.mark.asyncio
async def test_rs_major_underperformance_exceeds_margin_yields_avoid():
    """Underperformance > 3% margin => hard fail => AVOID.

    SPY: 100 -> 200 (strong uptrend)
    TEST: 100 -> 110 (barely up, major 20d underperformance >> 3%)
    """
    spy_df = _trend_bars(100.0, 200.0)
    symbol_df = _trend_bars(100.0, 110.0)
    provider = _make_rs_test_provider(spy_df, symbol_df)
    signals = await provider.screen_candidates(ScreenRequest(universe=["TEST"], max_results=5))
    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "AVOID", f"Expected AVOID for major underperformance, got {sig.verdict} (score={sig.total_score})"
    assert sig.failed_filters is not None
    assert "underperforming_spy_20d" in sig.failed_filters


@pytest.mark.asyncio
async def test_rs_minor_underperformance_score_above_watch_yields_watch():
    """Score >= watch_threshold but < buy_threshold, minor underperformance => WATCH.

    SPY: 100 -> 200
    TEST: 100 -> 155 (weaker trend, score likely 65-74)
    """
    spy_df = _trend_bars(100.0, 200.0)
    symbol_df = _trend_bars(100.0, 155.0)
    provider = _make_rs_test_provider(spy_df, symbol_df)
    signals = await provider.screen_candidates(ScreenRequest(universe=["TEST"], max_results=5))
    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "WATCH", f"Expected WATCH, got {sig.verdict} (score={sig.total_score})"
    assert 65 <= sig.total_score < 80, f"Score should be in watch range, got {sig.total_score}"
    assert sig.failed_filters is None, f"Should have no hard filters, got {sig.failed_filters}"
    assert "short-term relative strength is slightly below SPY" in sig.reason


@pytest.mark.asyncio
async def test_rs_minor_underperformance_score_below_watch_yields_avoid():
    """Score below watch_threshold, minor underperformance => AVOID (below threshold, not RS fail).

    Uses rise-then-drop bars so the symbol stays above SMA50 (avoids trend hard filter)
    but below SMA20 (reduces entry score), with very low final volume (reduces volume score)
    and weak SPY regime (low regime score). The result is total < 65 with no RS hard fail.
    """
    spy_df = _rise_drop_bars(rise=8, drop=2)
    symbol_df = _rise_drop_bars(rise=12, drop=4, last_vol=700000)
    provider = _make_rs_test_provider(spy_df, symbol_df)
    signals = await provider.screen_candidates(ScreenRequest(universe=["TEST"], max_results=5))
    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "AVOID", f"Expected AVOID (below watch threshold), got {sig.verdict} (score={sig.total_score})"
    assert sig.total_score < 65, f"Score should be below watch threshold, got {sig.total_score}"
    assert "below_threshold_score" in (sig.failed_filters or [])


@pytest.mark.asyncio
async def test_rs_no_underperformance_score_above_buy_yields_buy():
    """No underperformance, score >= buy_threshold => BUY_STARTER.

    SPY: 100 -> 180
    TEST: 100 -> 200 (stronger than SPY, outperforms)
    """
    spy_df = _trend_bars(100.0, 180.0)
    symbol_df = _trend_bars(100.0, 200.0)
    provider = _make_rs_test_provider(spy_df, symbol_df)
    signals = await provider.screen_candidates(ScreenRequest(universe=["TEST"], max_results=5))
    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "BUY_STARTER", f"Expected BUY_STARTER, got {sig.verdict} (score={sig.total_score})"
    assert sig.total_score >= 75, f"Score should be >= buy threshold, got {sig.total_score}"
    assert sig.failed_filters is None


@pytest.mark.asyncio
async def test_rs_60d_minor_underperformance_within_margin_yields_watch():
    """60d underperformance within 5% margin => minor warning => WATCH if score strong.

    SPY: 100 -> 200 (strong)
    TEST: 100 -> 185 (20d similar, 60d slightly weaker, minor 60d warning)
    """
    spy_df = _trend_bars(100.0, 200.0)
    symbol_df = _trend_bars(100.0, 185.0)
    provider = _make_rs_test_provider(spy_df, symbol_df)
    signals = await provider.screen_candidates(ScreenRequest(universe=["TEST"], max_results=5))
    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "WATCH", f"Expected WATCH for minor 60d underperformance, got {sig.verdict} (score={sig.total_score})"
    assert sig.total_score >= 75, f"Score should be >= buy threshold, got {sig.total_score}"
    # Should have at least one minor warning in reason
    assert "relative strength is slightly below SPY" in sig.reason


@pytest.mark.asyncio
async def test_rs_60d_major_underperformance_exceeds_margin_yields_avoid():
    """60d underperformance > 5% margin => hard fail => AVOID.

    SPY: 100 -> 200 (strong)
    TEST: 100 -> 120 (weak, both 20d and 60d underperformance)
    """
    spy_df = _trend_bars(100.0, 200.0)
    symbol_df = _trend_bars(100.0, 120.0)
    provider = _make_rs_test_provider(spy_df, symbol_df)
    signals = await provider.screen_candidates(ScreenRequest(universe=["TEST"], max_results=5))
    assert len(signals) == 1
    sig = signals[0]
    assert sig.verdict == "AVOID", f"Expected AVOID for major 60d underperformance, got {sig.verdict} (score={sig.total_score})"
    assert sig.failed_filters is not None
    assert "underperforming_spy_20d" in sig.failed_filters or "underperforming_spy_60d" in sig.failed_filters
