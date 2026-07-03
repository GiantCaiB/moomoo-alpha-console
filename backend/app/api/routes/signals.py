from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.signal import SignalResponse, SignalScoreResponse
from app.models.signal import Signal
from app.models.signal_score import SignalScore
from app.db.session import get_session
from app.strategies.momentum_relative_strength import run_momentum_screener

router = APIRouter()


@router.get("/api/v1/signals", response_model=list[SignalResponse])
async def list_signals(
    include_history: bool = False,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Signal).order_by(Signal.created_at.desc()).limit(50)
    )
    signals = result.scalars().all()

    if not include_history:
        seen: set[str] = set()
        deduped: list[Signal] = []
        for sig in signals:
            if sig.symbol not in seen:
                seen.add(sig.symbol)
                deduped.append(sig)
        signals = deduped

    responses = []
    for sig in signals:
        score_result = await session.execute(
            select(SignalScore).where(SignalScore.signal_id == sig.id)
        )
        scores = score_result.scalars().all()
        responses.append(SignalResponse(
            id=sig.id,
            symbol=sig.symbol,
            verdict=sig.verdict,
            total_score=sig.total_score,
            scores=[SignalScoreResponse(
                category=s.category,
                score=s.score,
                max_score=s.max_score,
                details=s.details,
            ) for s in scores],
            reason=sig.reason,
            entry_min=sig.entry_min,
            entry_max=sig.entry_max,
            stop_level=sig.stop_level,
            target_size_pct=sig.target_size_pct,
            risk_amount=sig.risk_amount,
            invalidation=sig.invalidation,
            current_price=sig.current_price,
            approved=sig.approved,
            signal_date=sig.signal_date,
            created_at=sig.created_at,
        ))
    return responses


@router.post("/api/v1/signals/run")
async def run_signals(session: AsyncSession = Depends(get_session)):
    strategy_run = await run_momentum_screener(session)
    return {
        "success": True,
        "strategy_run_id": strategy_run.id,
        "status": strategy_run.status,
        "signals_generated": strategy_run.signals_generated,
    }
