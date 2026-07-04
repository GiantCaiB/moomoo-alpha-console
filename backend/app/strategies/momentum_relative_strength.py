"""Momentum Relative Strength strategy runner."""
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_kline_service, get_price_resolver, get_runtime_state
from app.models.signal import Signal
from app.models.signal_score import SignalScore
from app.models.strategy_run import StrategyRun
from app.services.research.base import ScreenRequest
from app.services.research.moomoo_momentum import MoomooMomentumResearchProvider
from app.services.kline.symbol_map import normalize_symbol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpyReferenceData:
    symbol: str
    kline_fetch_attempted: bool
    cache_rows_before: int
    upstream_fetch_attempted: bool
    upstream_rows: int
    bars_after_fetch: int
    latest_bar_date: str | None
    last_error: str | None

    @property
    def is_ready(self) -> bool:
        return self.bars_after_fetch >= 200 and self.last_error is None

    def to_dict(self) -> dict:
        return asdict(self)


def _sanitize_universe(universe: list[str]) -> list[str]:
    cleaned: list[str] = []
    invalid: list[str] = []
    for raw in universe:
        normalized = normalize_symbol(raw)
        if normalized:
            cleaned.append(normalized)
        else:
            invalid.append(raw)
    if invalid:
        logger.warning("Skipping invalid symbols from trading universe: %s", invalid)
    return cleaned


async def run_momentum_screener(session: AsyncSession) -> StrategyRun:
    runtime_state_service = get_runtime_state()
    runtime_state = await runtime_state_service.build(session)

    strategy_run = StrategyRun(
        strategy_name="momentum_relative_strength",
        status="RUNNING",
        symbols_screened=0,
        signals_generated=0,
        data_error_count=0,
        data_source=runtime_state.signal_data_source,
        started_at=datetime.now(timezone.utc),
    )
    session.add(strategy_run)
    await session.flush()

    try:
        spy_reference = await _load_spy_reference(session)
        setattr(strategy_run, "spy_reference", spy_reference.to_dict())
        strategy_run.universe_source = runtime_state.trading_universe_source
        if not spy_reference.is_ready:
            strategy_run.status = "FAILED"
            strategy_run.error = "SPY reference data unavailable"
            strategy_run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return strategy_run

        sanitized_universe = _sanitize_universe(runtime_state.trading_universe)

        if runtime_state.mock_enabled:
            from app.services.research.local_momentum import LocalMomentumResearchProvider

            provider = LocalMomentumResearchProvider()
        else:
            provider = MoomooMomentumResearchProvider(
                price_resolver=get_price_resolver(),
                kline_service=get_kline_service(),
                signal_data_source=runtime_state.signal_data_source,
            )
        request = ScreenRequest(
            universe=sanitized_universe,
            max_results=len(sanitized_universe) if sanitized_universe else 10,
            min_score=0,
        )
        if runtime_state.mock_enabled:
            signals = await provider.screen_candidates(request)
        else:
            signals = await provider.screen_candidates(request, session=session)

        error_count = 0
        for sig_dto in signals:
            if sig_dto.verdict == "DATA_ERROR":
                error_count += 1
                strategy_run.error = (strategy_run.error or "") + f"{sig_dto.symbol}: {sig_dto.reason}; "

            signal = Signal(
                strategy_run_id=strategy_run.id,
                symbol=sig_dto.symbol,
                verdict=sig_dto.verdict,
                total_score=sig_dto.total_score,
                reason=sig_dto.reason,
                entry_min=sig_dto.entry_min,
                entry_max=sig_dto.entry_max,
                stop_level=sig_dto.stop_level,
                target_size_pct=sig_dto.target_size_pct,
                risk_amount=sig_dto.risk_amount,
                invalidation=sig_dto.invalidation,
                current_price=sig_dto.current_price,
                signal_date=datetime.now(timezone.utc),
                strategy_name=sig_dto.strategy_name,
                data_source=sig_dto.data_source,
                generated_at=sig_dto.generated_at,
                universe_json=json.dumps(sig_dto.universe) if sig_dto.universe else None,
                price_source=sig_dto.price_source,
                bar_source=sig_dto.bar_source,
                is_real_market_data=sig_dto.is_real_market_data,
                is_tradeable=sig_dto.is_tradeable,
                has_error=sig_dto.verdict == "DATA_ERROR",
                failed_filters=json.dumps(sig_dto.failed_filters) if sig_dto.failed_filters else None,
                data_quality_status=sig_dto.data_quality_status,
                calculated_score_before_filters=sig_dto.calculated_score_before_filters,
            )
            session.add(signal)
            await session.flush()

            if sig_dto.verdict != "DATA_ERROR":
                for score_dict in sig_dto.scores:
                    session.add(
                        SignalScore(
                            signal_id=signal.id,
                            category=score_dict["category"],
                            score=score_dict["score"],
                            max_score=score_dict["max_score"],
                            details=score_dict["details"],
                        )
                    )

        strategy_run.symbols_screened = len(sanitized_universe)
        strategy_run.signals_generated = len(signals) - error_count
        strategy_run.data_error_count = error_count
        strategy_run.status = "COMPLETED"
        if error_count > 0:
            strategy_run.error = (strategy_run.error or "").rstrip("; ")
        strategy_run.completed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info("Screener complete: %d signals generated, %d data errors", strategy_run.signals_generated, error_count)
    except Exception as exc:
        strategy_run.status = "FAILED"
        strategy_run.error = str(exc)
        await session.commit()
        logger.error("Screener failed: %s", exc)

    return strategy_run


async def _load_spy_reference(session: AsyncSession) -> SpyReferenceData:
    kline = get_kline_service()
    pre_status = await kline.get_symbol_status("SPY", session=session)
    cache_rows_before = int(pre_status.get("cached_bar_count", 0) or 0)

    try:
        spy_result = await kline.get_cached_or_fetch_daily_bars("SPY", lookback_days=400, session=session)
        bars_after_fetch = len(spy_result.bars)
        latest_bar_date = spy_result.latest_cached_bar_date
        if latest_bar_date is None and not spy_result.bars.empty:
            latest_row = spy_result.bars.iloc[-1]
            latest_bar = latest_row.get("date") if "date" in spy_result.bars.columns else latest_row.get("bar_date")
            if hasattr(latest_bar, "isoformat"):
                latest_bar_date = latest_bar.isoformat()
            elif latest_bar is not None:
                latest_bar_date = str(latest_bar)
        last_error = spy_result.fetch_error
        if bars_after_fetch == 0 and last_error is None:
            last_error = "No SPY reference data available"
        elif bars_after_fetch < 200 and last_error is None:
            last_error = f"insufficient history ({bars_after_fetch} bars)"
        return SpyReferenceData(
            symbol="SPY",
            kline_fetch_attempted=True,
            cache_rows_before=cache_rows_before,
            upstream_fetch_attempted=bool(spy_result.fetch_attempted),
            upstream_rows=bars_after_fetch if spy_result.fetch_attempted else 0,
            bars_after_fetch=bars_after_fetch,
            latest_bar_date=latest_bar_date,
            last_error=last_error,
        )
    except Exception as exc:
        return SpyReferenceData(
            symbol="SPY",
            kline_fetch_attempted=True,
            cache_rows_before=cache_rows_before,
            upstream_fetch_attempted=True,
            upstream_rows=0,
            bars_after_fetch=0,
            latest_bar_date=None,
            last_error=str(exc),
        )
