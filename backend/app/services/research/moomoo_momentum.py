"""
Moomoo Momentum + Relative Strength Screener.

Uses the runtime price resolver and KLineService only.
No mock data, no local synthetic bars, and no moomoo historical pulls.
"""
import logging
from datetime import date, datetime, timezone
from statistics import mean

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_data.base import BarData
from app.services.market_data.price_resolver import PriceResolver, PriceResolution
from app.services.kline.service import KLineService
from app.services.research.base import ResearchReport, ScreenRequest, SignalDto

logger = logging.getLogger(__name__)


def _df_to_bars(df: pd.DataFrame, symbol: str) -> list[BarData]:
    bars: list[BarData] = []
    for _, row in df.iterrows():
        current_date = row["date"]
        if hasattr(current_date, "to_pydatetime"):
            current_date = current_date.to_pydatetime().date()
        elif hasattr(current_date, "date"):
            current_date = current_date.date()
        elif isinstance(current_date, str):
            current_date = date.fromisoformat(current_date[:10])
        bars.append(
            BarData(
                symbol=symbol,
                bar_date=current_date,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return bars


def _sma(bars: list[BarData], period: int) -> float | None:
    if len(bars) < period:
        return None
    return mean(bar.close for bar in bars[-period:])


def _return_pct(bars: list[BarData], period: int) -> float | None:
    if len(bars) < period + 1:
        return None
    start = bars[-(period + 1)].close
    end = bars[-1].close
    if start <= 0:
        return None
    return (end - start) / start * 100


def _avg_volume(bars: list[BarData], period: int) -> float | None:
    if len(bars) < period:
        return None
    return mean(bar.volume for bar in bars[-period:])


def _estimate_atr(bars: list[BarData], period: int = 14) -> float | None:
    if len(bars) < period + 1:
        return None
    trs: list[float] = []
    for index in range(-period, 0):
        prev_close = bars[index - 1].close
        high = bars[index].high
        low = bars[index].low
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return mean(trs)


def _score_trend(close: float, sma50: float | None, sma200: float | None, sma20: float | None) -> float:
    score = 0.0
    if sma50 and close > sma50:
        score += 10
        pct_above = (close / sma50 - 1) * 100
        score += 5 if 2 <= pct_above <= 8 else 2
    if sma200 and close > sma200:
        score += 10
    return min(score, 25)


def _score_relative_strength(ret_20d: float, ret_60d: float, spy_20d: float, spy_60d: float) -> float:
    score = 0.0
    score += 12 if ret_20d > spy_20d * 1.5 else 8 if ret_20d > spy_20d else 4
    score += 8 if ret_60d > spy_60d else 4
    return min(score, 20)


def _score_volume(current: float, avg: float) -> float:
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


def _score_entry_quality(close: float, sma20: float | None, sma50: float | None) -> float:
    score = 0.0
    if sma20:
        pct_from_sma20 = (close / sma20 - 1) * 100
        score += 8 if 0 < pct_from_sma20 < 3 else 4 if pct_from_sma20 < 0 else 2
    if sma50:
        pct_from_sma50 = (close / sma50 - 1) * 100
        score += 7 if 0 < pct_from_sma50 < 5 else 3
    return min(score, 15)


def _score_risk_reward(close: float, atr: float | None) -> float:
    if atr and atr > 0 and close > 0:
        atr_pct = (atr / close) * 100
        if atr_pct < 1.0:
            return 14.0
        if atr_pct < 2.0:
            return 12.0
        if atr_pct < 3.0:
            return 10.0
        if atr_pct < 4.0:
            return 8.0
        return 6.0
    return 10.0


def _score_market_regime(spy_bars: list[BarData]) -> float:
    spy_ret_20d = _return_pct(spy_bars, 20) or 0
    if spy_ret_20d > 3:
        return 15.0
    if spy_ret_20d > 0:
        return 12.0
    if spy_ret_20d > -3:
        return 8.0
    return 4.0


class MoomooMomentumResearchProvider:
    def __init__(
        self,
        *,
        price_resolver: PriceResolver,
        kline_service: KLineService,
        signal_data_source: str,
        strategy_profile_id: str | None = None,
        strategy_version: str | None = None,
        parameters: dict | None = None,
    ) -> None:
        self._price_resolver = price_resolver
        self._kline = kline_service
        self._signal_data_source = signal_data_source
        self._strategy_profile_id = strategy_profile_id
        self._strategy_version = strategy_version
        self._parameters = parameters or {}

    @property
    def _buy_threshold(self) -> float:
        return float(self._parameters.get("buy_score_threshold", 75))

    @property
    def _watch_threshold(self) -> float:
        return float(self._parameters.get("watch_score_threshold", 65))

    @property
    def _min_bars(self) -> int:
        return int(self._parameters.get("min_bars", 220))

    def _build_signal_dto(self, symbol: str, verdict: str, total_score: float,
                          scores: list[dict], reason: str,
                          entry_min: float | None, entry_max: float | None,
                          stop_level: float | None,
                          target_size_pct: float | None,
                          risk_amount: float | None,
                          current_price: float | None,
                          universe: list[str],
                          price_source: str,
                          failed_filters: list[str] | None,
                          data_quality_status: str,
                          calculated_score_before_filters: float | None,
                          invalidation: str | None = None,
                          is_tradeable: bool = False,
                          price_as_of: str | None = None) -> SignalDto:
        return SignalDto(
            symbol=symbol,
            verdict=verdict,
            total_score=round(total_score, 1),
            scores=scores,
            reason=reason,
            entry_min=entry_min,
            entry_max=entry_max,
            stop_level=stop_level,
            target_size_pct=target_size_pct,
            risk_amount=risk_amount,
            invalidation=invalidation,
            current_price=current_price,
            strategy_name="momentum_relative_strength",
            data_source=self._signal_data_source,
            generated_at=datetime.now(timezone.utc),
            universe=list(universe),
            price_source=price_source,
            bar_source="yfinance_cached_daily_bars",
            is_real_market_data=True,
            is_tradeable=is_tradeable,
            has_error=False,
            failed_filters=failed_filters,
            data_quality_status=data_quality_status,
            calculated_score_before_filters=calculated_score_before_filters,
            price_as_of=price_as_of,
            strategy_profile_id=self._strategy_profile_id,
            strategy_version=self._strategy_version,
            parameters_snapshot=self._parameters,
        )

    async def screen_candidates(self, request: ScreenRequest, session: AsyncSession | None = None) -> list[SignalDto]:
        results: list[SignalDto] = []

        try:
            spy_fetch = await self._kline.get_cached_or_fetch_daily_bars("SPY", lookback_days=400, session=session)
            spy_df = spy_fetch.bars
            spy_bars = _df_to_bars(spy_df, "SPY")
        except Exception as exc:
            logger.error("SPY data unavailable, cannot run screener: %s", exc)
            return [self._error_signal("SPY", "Cannot run screener without SPY reference data", "PROVIDER_ERROR", request.universe)]

        spy_20d = _return_pct(spy_bars, 20) or 0
        spy_60d = _return_pct(spy_bars, 60) or 0

        for symbol in request.universe:
            if symbol.upper() == "SPY":
                continue
            results.append(await self._screen_one(symbol, spy_bars, spy_20d, spy_60d, request.universe, session=session))

        results.sort(key=lambda signal: signal.total_score, reverse=True)
        return results[:request.max_results]

    async def _screen_one(
        self,
        symbol: str,
        spy_bars: list[BarData],
        spy_20d: float,
        spy_60d: float,
        universe: list[str],
        session: AsyncSession | None = None,
    ) -> SignalDto:
        try:
            kline_result = await self._kline.get_cached_or_fetch_daily_bars(symbol, lookback_days=400, session=session)
            bars_df = kline_result.bars
            bars = _df_to_bars(bars_df, symbol)
        except Exception as exc:
            message = str(exc)
            quality = "INSUFFICIENT_HISTORY" if "insufficient history" in message.lower() or "less than 200" in message.lower() else "PROVIDER_ERROR"
            return self._error_signal(symbol, message, quality, universe)

        if bars_df.empty:
            message = kline_result.fetch_error or "No bar data available"
            if "insufficient" in message.lower() or "less than 200" in message.lower():
                quality = "INSUFFICIENT_HISTORY"
            else:
                quality = "PROVIDER_ERROR" if kline_result.fetch_failed else "INSUFFICIENT_HISTORY"
            return self._error_signal(symbol, message, quality, universe)

        min_bars = self._min_bars
        if len(bars) < min_bars:
            return self._error_signal(
                symbol,
                f"Insufficient history: {len(bars)} bars (< {min_bars} required)",
                "INSUFFICIENT_HISTORY",
                universe,
            )

        price_resolution = await self._price_resolver.resolve(symbol, bars=bars_df, session=session)
        if price_resolution.price is None:
            return self._error_from_resolution(symbol, price_resolution, "DATA_ERROR", universe)

        close = float(price_resolution.price)
        sma50 = _sma(bars, 50)
        sma200 = _sma(bars, 200)
        sma20 = _sma(bars, 20)
        ret_20d = _return_pct(bars, 20) or 0
        ret_60d = _return_pct(bars, 60) or 0
        avg_vol_20 = _avg_volume(bars, 20) or 0
        current_vol = bars[-1].volume
        atr = _estimate_atr(bars, 14)

        total, scores = self._compute_scores(close, sma50, sma200, sma20, ret_20d, ret_60d, spy_20d, spy_60d, current_vol, avg_vol_20, spy_bars, atr)
        failed_filters: list[str] = []
        hard_reasons: list[str] = []

        if sma50 is None or close <= sma50:
            failed_filters.append("price_below_sma50")
            hard_reasons.append("Price below 50 SMA")
        if sma200 is None or close <= sma200:
            failed_filters.append("price_below_sma200")
            hard_reasons.append("Price below 200 SMA")
        if ret_20d < spy_20d:
            failed_filters.append("underperforming_spy_20d")
            hard_reasons.append(f"20d return {ret_20d:.1f}% < SPY {spy_20d:.1f}%")
        if ret_60d < spy_60d:
            failed_filters.append("underperforming_spy_60d")
            hard_reasons.append(f"60d return {ret_60d:.1f}% < SPY {spy_60d:.1f}%")
        if avg_vol_20 > 0 and current_vol < avg_vol_20 * 0.5:
            failed_filters.append("volume_ratio_below_threshold")
            hard_reasons.append("Volume significantly below average")
        if sma20 and close > sma20 * 1.15:
            failed_filters.append("price_too_far_above_sma20")
            hard_reasons.append(f"Price {((close / sma20 - 1) * 100):.1f}% above 20 SMA (> 15% max)")

        buy_threshold = self._buy_threshold
        watch_threshold = self._watch_threshold

        if failed_filters:
            verdict = "AVOID"
            reason = "; ".join(hard_reasons)
        elif total >= buy_threshold:
            verdict = "BUY_STARTER"
            reason = f"Score: {total:.1f}/100"
        elif total >= watch_threshold:
            verdict = "WATCH"
            reason = f"Score: {total:.1f}/100 — borderline, monitor for improvement"
        else:
            verdict = "AVOID"
            failed_filters.append("below_threshold_score")
            reason = f"Score: {total:.1f}/100 — insufficient setup quality"

        stop = self._compute_stop(close, sma20, bars)

        return self._build_signal_dto(
            symbol=symbol,
            verdict=verdict,
            total_score=total,
            scores=scores,
            reason=reason,
            entry_min=round(close * 0.98, 2),
            entry_max=close,
            stop_level=stop,
            target_size_pct=2.0 if verdict == "BUY_STARTER" else None,
            risk_amount=round((close - stop) * 100, 2),
            current_price=close,
            universe=universe,
            price_source=price_resolution.price_source,
            failed_filters=failed_filters if failed_filters else None,
            data_quality_status="OK",
            calculated_score_before_filters=round(total, 1),
            invalidation=f"Close below ${stop:.2f} or 20d return < SPY" if verdict != "DATA_ERROR" else None,
            price_as_of=price_resolution.price_timestamp,
        )

    def _error_from_resolution(
        self,
        symbol: str,
        price_resolution: PriceResolution,
        quality: str,
        universe: list[str],
    ) -> SignalDto:
        return SignalDto(
            symbol=symbol,
            verdict="DATA_ERROR",
            total_score=0.0,
            scores=[],
            reason=price_resolution.error or "No price data available",
            has_error=True,
            error_message=price_resolution.error or "No price data available",
            current_price=None,
            strategy_name="momentum_relative_strength",
            data_source=self._signal_data_source,
            generated_at=datetime.now(timezone.utc),
            universe=list(universe),
            price_source=price_resolution.price_source,
            bar_source="yfinance_cached_daily_bars",
            is_real_market_data=True,
            is_tradeable=False,
            failed_filters=None,
            data_quality_status=quality,
            calculated_score_before_filters=None,
            strategy_profile_id=self._strategy_profile_id,
            strategy_version=self._strategy_version,
            parameters_snapshot=self._parameters,
        )

    def _error_signal(self, symbol: str, error: str, quality: str, universe: list[str]) -> SignalDto:
        return SignalDto(
            symbol=symbol,
            verdict="DATA_ERROR",
            total_score=0.0,
            scores=[],
            reason=error,
            has_error=True,
            error_message=error,
            current_price=None,
            strategy_name="momentum_relative_strength",
            data_source=self._signal_data_source,
            generated_at=datetime.now(timezone.utc),
            universe=list(universe),
            price_source="DATA_ERROR",
            bar_source="yfinance_cached_daily_bars",
            is_real_market_data=True,
            is_tradeable=False,
            failed_filters=None,
            data_quality_status=quality,
            calculated_score_before_filters=None,
            strategy_profile_id=self._strategy_profile_id,
            strategy_version=self._strategy_version,
            parameters_snapshot=self._parameters,
        )

    async def analyze_symbol(self, symbol: str, session: AsyncSession | None = None) -> ResearchReport:
        try:
            df = await self._kline.get_daily_bars(symbol, lookback_days=400, session=session)
            bars = _df_to_bars(df, symbol)
        except Exception as exc:
            return ResearchReport(symbol=symbol, summary=str(exc), metrics={})
        if not bars:
            return ResearchReport(symbol=symbol, summary="No data available", metrics={})
        return ResearchReport(
            symbol=symbol,
            summary=f"{symbol} at ${bars[-1].close:.2f}",
            metrics={"close": bars[-1].close, "sma50": _sma(bars, 50), "sma200": _sma(bars, 200)},
        )

    def _compute_stop(self, close: float, sma20: float | None, bars: list[BarData]) -> float:
        atr = _estimate_atr(bars, 14)
        if atr and atr > 0:
            return round(close - (atr * 2), 2)
        if sma20:
            return round(sma20 * 0.97, 2)
        return round(close * 0.95, 2)

    def _compute_scores(
        self,
        close: float,
        sma50: float | None,
        sma200: float | None,
        sma20: float | None,
        ret_20d: float,
        ret_60d: float,
        spy_20d: float,
        spy_60d: float,
        current_vol: float,
        avg_vol_20: float,
        spy_bars: list[BarData],
        atr: float | None = None,
    ) -> tuple[float, list[dict]]:
        trend = _score_trend(close, sma50, sma200, sma20)
        rs = _score_relative_strength(ret_20d, ret_60d, spy_20d, spy_60d)
        vol = _score_volume(current_vol, avg_vol_20)
        entry = _score_entry_quality(close, sma20, sma50)
        rr = _score_risk_reward(close, atr)
        regime = _score_market_regime(spy_bars)
        total = trend + rs + vol + entry + rr + regime
        scores = [
            {"category": "Trend", "score": trend, "max_score": 25, "details": f"SMA50={sma50:.2f}, SMA200={sma200:.2f}"},
            {"category": "Relative Strength", "score": rs, "max_score": 20, "details": f"20d={ret_20d:.1f}%, 60d={ret_60d:.1f}%"},
            {"category": "Volume Confirmation", "score": vol, "max_score": 10, "details": f"Vol={current_vol:.0f}, Avg20={avg_vol_20:.0f}"},
            {"category": "Entry Quality", "score": entry, "max_score": 15, "details": f"Distance from SMA20={((close / sma20 - 1) * 100) if sma20 else 0:.1f}%"},
            {"category": "Risk/Reward", "score": rr, "max_score": 15, "details": "Estimated from ATR-based volatility"},
            {"category": "Market Regime", "score": regime, "max_score": 15, "details": f"SPY 20d={spy_20d:.1f}%"},
        ]
        return total, scores
