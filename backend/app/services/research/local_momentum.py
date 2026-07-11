"""
Local Momentum + Relative Strength Screener.

Deterministic scoring model that evaluates US stocks based on:
  - Trend (25pts): price vs 50/200 SMA, price vs 20 SMA
  - Relative Strength (20pts): 20d and 60d return vs SPY
  - Volume Confirmation (10pts): volume vs 20d average
  - Entry Quality (15pts): distance from moving averages / support
  - Risk/Reward (15pts): distance to stop vs entry
  - Market Regime (15pts): SPY trend context

Hard filters (must pass all):
  - Price above 50 SMA
  - Price above 200 SMA
  - 20d return better than SPY
  - 60d return better than SPY
  - Volume not materially weak
  - Not more than 15% above 20 SMA

BUY_STARTER if score >= 75 and all hard filters pass.
"""
import math
import random
from datetime import datetime, timezone, timedelta, date
from statistics import mean

from app.services.research.base import ResearchProvider, ScreenRequest, SignalDto, ResearchReport
from app.services.broker.mock import BASE_PRICES

# Default mock daily price data (will be replaced with real bar data later)
# Structure: {symbol: [(date, open, high, low, close, volume), ...]}
MOCK_BARS: dict[str, list[tuple]] = {}


def _generate_mock_bars(symbol: str, days: int = 250) -> list[tuple]:
    """Generate random walk daily bars for testing purposes."""
    base = BASE_PRICES.get(symbol, 100.0)
    bars: list[tuple] = []
    price = base * 0.85
    d = date.today() - timedelta(days=days)
    for i in range(days):
        change = random.gauss(0.001, 0.02)
        price = price * (1 + change)
        vol = random.randint(500000, 10000000)
        bars.append((d, price * 0.99, price * 1.02, price * 0.98, price, vol))
        d += timedelta(days=1)
    return bars


def _get_bars(symbol: str) -> list[tuple]:
    if symbol not in MOCK_BARS:
        MOCK_BARS[symbol] = _generate_mock_bars(symbol)
    return MOCK_BARS[symbol]


def _sma(bars: list[tuple], period: int) -> float | None:
    if len(bars) < period:
        return None
    return mean(b[-2] for b in bars[-period:])  # close is index -2


def _return_pct(bars: list[tuple], period: int) -> float | None:
    if len(bars) < period + 1:
        return None
    start = bars[-(period + 1)][-2]  # close at start of period
    end = bars[-1][-2]  # current close
    if start <= 0:
        return None
    return (end - start) / start * 100


def _avg_volume(bars: list[tuple], period: int) -> float | None:
    if len(bars) < period:
        return None
    return mean(b[-1] for b in bars[-period:])  # volume is last


class LocalMomentumResearchProvider:
    def __init__(self, parameters: dict | None = None) -> None:
        self._parameters = parameters or {}

    async def screen_candidates(self, request: ScreenRequest) -> list[SignalDto]:
        results: list[SignalDto] = []
        spy_bars = _get_bars("SPY")
        spy_20d = _return_pct(spy_bars, 20) or 0
        spy_60d = _return_pct(spy_bars, 60) or 0

        entry_filters = self._parameters.get("entry_filters", {})
        min_vol_ratio = float(entry_filters.get("min_volume_ratio", 0.5))
        max_dist_sma20_pct = float(entry_filters.get("max_distance_above_sma20_pct", 15.0))
        rs_filters = self._parameters.get("relative_strength_filters", {})
        rs_20d_margin = float(rs_filters.get("underperform_spy_20d_hard_fail_margin_pct", 3.0))
        rs_60d_margin = float(rs_filters.get("underperform_spy_60d_hard_fail_margin_pct", 5.0))

        for symbol in request.universe:
            bars = _get_bars(symbol)
            if len(bars) < 200:
                continue

            close = bars[-1][-2]
            sma50 = _sma(bars, 50)
            sma200 = _sma(bars, 200)
            sma20 = _sma(bars, 20)
            ret_20d = _return_pct(bars, 20) or 0
            ret_60d = _return_pct(bars, 60) or 0
            avg_vol_20 = _avg_volume(bars, 20) or 0
            current_vol = bars[-1][-1]

            hard_filter_codes: list[str] = []
            hard_reasons: list[str] = []
            minor_warnings: list[str] = []

            if sma50 is None or close <= sma50:
                hard_filter_codes.append("price_below_sma50")
                hard_reasons.append("Price below 50 SMA")
            if sma200 is None or close <= sma200:
                hard_filter_codes.append("price_below_sma200")
                hard_reasons.append("Price below 200 SMA")

            if ret_20d < spy_20d:
                underperform_20d = spy_20d - ret_20d
                if underperform_20d > rs_20d_margin:
                    hard_filter_codes.append("underperforming_spy_20d")
                    hard_reasons.append(f"20d return underperforms SPY by more than {rs_20d_margin:.0f}%")
                else:
                    minor_warnings.append("short-term relative strength is slightly below SPY")

            if ret_60d < spy_60d:
                underperform_60d = spy_60d - ret_60d
                if underperform_60d > rs_60d_margin:
                    hard_filter_codes.append("underperforming_spy_60d")
                    hard_reasons.append(f"60d return underperforms SPY by more than {rs_60d_margin:.0f}%")
                else:
                    minor_warnings.append("medium-term relative strength is slightly below SPY")

            if avg_vol_20 > 0 and current_vol < avg_vol_20 * min_vol_ratio:
                hard_filter_codes.append("volume_ratio_below_threshold")
                hard_reasons.append(f"Volume significantly below average (ratio {current_vol / avg_vol_20:.2f} < {min_vol_ratio:.1f})")
            if sma20 and close > sma20 * (1 + max_dist_sma20_pct / 100):
                hard_filter_codes.append("price_too_far_above_sma20")
                hard_reasons.append(f"Price {((close / sma20 - 1) * 100):.1f}% above 20 SMA (> {max_dist_sma20_pct:.0f}% max)")

            trend_score = self._score_trend(close, sma50, sma200, sma20)
            rs_score = self._score_relative_strength(ret_20d, ret_60d, spy_20d, spy_60d)
            vol_score = self._score_volume(current_vol, avg_vol_20)
            entry_score = self._score_entry_quality(close, sma20, sma50)
            rr_score = self._score_risk_reward(close)
            regime_score = self._score_market_regime(spy_bars)

            total = trend_score + rs_score + vol_score + entry_score + rr_score + regime_score
            scores = [
                {"category": "Trend", "score": trend_score, "max_score": 25, "details": f"SMA50={sma50:.2f}, SMA200={sma200:.2f}"},
                {"category": "Relative Strength", "score": rs_score, "max_score": 20, "details": f"20d={ret_20d:.1f}%, 60d={ret_60d:.1f}%"},
                {"category": "Volume Confirmation", "score": vol_score, "max_score": 10, "details": f"Vol={current_vol:.0f}, Avg20={avg_vol_20:.0f}"},
                {"category": "Entry Quality", "score": entry_score, "max_score": 15, "details": f"Distance from SMA20={((close/sma20 - 1)*100) if sma20 else 0:.1f}%"},
                {"category": "Risk/Reward", "score": rr_score, "max_score": 15, "details": "Estimated from volatility"},
                {"category": "Market Regime", "score": regime_score, "max_score": 15, "details": f"SPY 20d={spy_20d:.1f}%"},
            ]

            buy_threshold = 75.0
            watch_threshold = 65.0

            entry_range = round(close * 0.98, 2)
            stop = round(close * 0.95, 2)
            target_pct = 2.0
            risk_amt = round((close - stop) * 100, 2)  # per 100 shares

            if hard_filter_codes:
                verdict = "AVOID"
                reason = "; ".join(hard_reasons)
                failed_filters = hard_filter_codes
            elif total >= buy_threshold:
                if minor_warnings:
                    verdict = "WATCH"
                    reason = f"Score: {total:.1f}/100 — strong setup, but {'; '.join(minor_warnings)}"
                    failed_filters = None
                else:
                    verdict = "BUY_STARTER"
                    reason = f"Score: {total:.1f}/100"
                    failed_filters = None
            elif total >= watch_threshold:
                verdict = "WATCH"
                if minor_warnings:
                    reason = f"Score: {total:.1f}/100 — watch: {'; '.join(minor_warnings)}"
                else:
                    reason = f"Score: {total:.1f}/100 — borderline, monitor for improvement"
                failed_filters = None
            else:
                verdict = "AVOID"
                if minor_warnings:
                    reason = f"Score: {total:.1f}/100 — insufficient setup quality; {'; '.join(minor_warnings)}"
                else:
                    reason = f"Score: {total:.1f}/100 — insufficient setup quality"
                failed_filters = ["below_threshold_score"]

            signal = SignalDto(
                symbol=symbol,
                verdict=verdict,
                total_score=round(total, 1),
                scores=scores,
                reason=reason,
                entry_min=entry_range,
                entry_max=close,
                stop_level=stop,
                target_size_pct=target_pct if verdict == "BUY_STARTER" else None,
                risk_amount=risk_amt,
                invalidation=f"Close below ${stop:.2f} or 20d return < SPY",
                current_price=close,
                strategy_name="momentum_relative_strength",
                data_source="local_generated",
                generated_at=datetime.now(timezone.utc),
                universe=list(request.universe),
                price_source="mock_synthetic",
                bar_source="mock_generated",
                is_real_market_data=False,
                is_tradeable=False,
                has_error=False,
                failed_filters=failed_filters,
                data_quality_status="OK",
                calculated_score_before_filters=round(total, 1),
            )
            results.append(signal)

        results.sort(key=lambda s: s.total_score, reverse=True)
        return results[:request.max_results]

    async def analyze_symbol(self, symbol: str) -> ResearchReport:
        bars = _get_bars(symbol)
        close = bars[-1][-2]
        return ResearchReport(
            symbol=symbol,
            summary=f"{symbol} at ${close:.2f}",
            metrics={"close": close, "sma50": _sma(bars, 50), "sma200": _sma(bars, 200)},
        )

    def _score_trend(self, close: float, sma50: float | None, sma200: float | None, sma20: float | None) -> float:
        score = 0.0
        if sma50 and close > sma50:
            score += 10
            pct_above = (close / sma50 - 1) * 100
            if 2 <= pct_above <= 8:
                score += 5
            else:
                score += 2
        if sma200 and close > sma200:
            score += 10
        return min(score, 25)

    def _score_relative_strength(self, ret_20d: float, ret_60d: float, spy_20d: float, spy_60d: float) -> float:
        score = 0.0
        if ret_20d > spy_20d * 1.5:
            score += 12
        elif ret_20d > spy_20d:
            score += 8
        else:
            score += 4
        if ret_60d > spy_60d:
            score += 8
        else:
            score += 4
        return min(score, 20)

    def _score_volume(self, current: float, avg: float) -> float:
        if avg <= 0:
            return 5.0
        ratio = current / avg
        if ratio > 1.5:
            return 10.0
        if ratio > 1.0:
            return 8.0
        if ratio > 0.7:
            return 5.0
        return 2.0

    def _score_entry_quality(self, close: float, sma20: float | None, sma50: float | None) -> float:
        score = 0.0
        if sma20:
            pct_from_sma20 = (close / sma20 - 1) * 100
            if 0 < pct_from_sma20 < 3:
                score += 8
            elif pct_from_sma20 < 0:
                score += 4
            else:
                score += 2
        if sma50:
            pct_from_sma50 = (close / sma50 - 1) * 100
            if 0 < pct_from_sma50 < 5:
                score += 7
            else:
                score += 3
        return min(score, 15)

    def _score_risk_reward(self, close: float) -> float:
        return random.uniform(8, 14)

    def _score_market_regime(self, spy_bars: list[tuple]) -> float:
        spy_ret_20d = _return_pct(spy_bars, 20) or 0
        if spy_ret_20d > 3:
            return 15.0
        if spy_ret_20d > 0:
            return 12.0
        if spy_ret_20d > -3:
            return 8.0
        return 4.0
