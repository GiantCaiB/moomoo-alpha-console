"""
Momentum Relative Strength Strategy.

Wraps LocalMomentumResearchProvider as a callable strategy
that can be invoked by the scheduler or API.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import Signal
from app.models.signal_score import SignalScore
from app.models.strategy_run import StrategyRun
from app.services.research.local_momentum import LocalMomentumResearchProvider
from app.services.research.base import ScreenRequest
from app.core.config import settings

logger = logging.getLogger(__name__)


async def run_momentum_screener(session: AsyncSession) -> StrategyRun:
    provider = LocalMomentumResearchProvider()
    strategy_run = StrategyRun(
        strategy_name="momentum_relative_strength",
        status="RUNNING",
        symbols_screened=0,
        signals_generated=0,
        started_at=datetime.now(timezone.utc),
    )
    session.add(strategy_run)
    await session.flush()

    try:
        request = ScreenRequest(
            universe=settings.universe_symbols,
            max_results=len(settings.universe_symbols),
            min_score=0,
        )
        signals = await provider.screen_candidates(request)

        for sig_dto in signals:
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
            )
            session.add(signal)
            await session.flush()

            for score_dict in sig_dto.scores:
                score = SignalScore(
                    signal_id=signal.id,
                    category=score_dict["category"],
                    score=score_dict["score"],
                    max_score=score_dict["max_score"],
                    details=score_dict["details"],
                )
                session.add(score)

        strategy_run.symbols_screened = len(settings.universe_symbols)
        strategy_run.signals_generated = len(signals)
        strategy_run.status = "COMPLETED"
        strategy_run.completed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info("Screener complete: %d signals generated", len(signals))
    except Exception as e:
        strategy_run.status = "FAILED"
        strategy_run.error = str(e)
        await session.commit()
        logger.error("Screener failed: %s", e)

    return strategy_run
