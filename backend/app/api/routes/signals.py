import json
from collections import OrderedDict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.signal import SignalResponse, SignalScoreResponse, StaleSignalCountResponse
from app.models.signal import Signal
from app.models.strategy_profile import StrategyProfile
from app.models.signal_score import SignalScore
from app.db.session import get_session
from app.api.dependencies import get_runtime_state
from app.strategies.momentum_relative_strength import run_momentum_screener
from app.services.kline.symbol_map import normalize_symbol


class RunSignalsRequest(BaseModel):
    strategy_profile_id: str | None = None

router = APIRouter()

STALE_LOCAL_DATA_SOURCES = {"local_generated", "mock"}
REAL_SIGNAL_DATA_SOURCES = {"moomoo", "moomoo_snapshot_plus_yfinance_kline"}


@router.get("/api/v1/signals", response_model=list[SignalResponse])
async def list_signals(
    include_history: bool = False,
    include_local: bool = False,
    session: AsyncSession = Depends(get_session),
):
    query = select(Signal).order_by(Signal.created_at.desc()).limit(50)

    runtime_state = await get_runtime_state().build(session)
    if runtime_state.read_only and not include_local:
        universe = runtime_state.trading_universe
        query = query.where(
            Signal.data_source.in_([runtime_state.signal_data_source, "moomoo"]),
            Signal.is_real_market_data == True,
            Signal.symbol.in_(universe),
        )

    result = await session.execute(query)
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
        universe_list: list[str] | None = None
        if sig.universe_json:
            universe_list = json.loads(sig.universe_json)

        failed_filters_list: list[str] | None = None
        if sig.failed_filters:
            failed_filters_list = json.loads(sig.failed_filters)

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
            strategy_name=sig.strategy_name,
            data_source=sig.data_source,
            generated_at=sig.generated_at,
            universe=universe_list,
            price_source=sig.price_source,
            bar_source=sig.bar_source,
            is_real_market_data=sig.is_real_market_data,
            is_tradeable=sig.is_tradeable,
            has_error=sig.has_error,
            failed_filters=failed_filters_list,
            data_quality_status=sig.data_quality_status,
            calculated_score_before_filters=sig.calculated_score_before_filters,
        ))
    return responses


@router.post("/api/v1/signals/run")
async def run_signals(
    req: RunSignalsRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    strategy_profile_id = None
    strategy_version = None
    parameters = None

    if req and req.strategy_profile_id:
        result = await session.execute(
            select(StrategyProfile).where(StrategyProfile.id == req.strategy_profile_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            return {"success": False, "error": f"Strategy profile {req.strategy_profile_id} not found"}
        strategy_profile_id = profile.id
        strategy_version = profile.version
        parameters = json.loads(profile.parameters_json) if profile.parameters_json else {}

    strategy_run = await run_momentum_screener(
        session,
        strategy_profile_id=strategy_profile_id,
        strategy_version=strategy_version,
        parameters=parameters,
    )
    runtime_state = await get_runtime_state().build(session)
    universe = runtime_state.trading_universe
    symbols_scanned = [symbol for symbol in (normalize_symbol(item) for item in universe) if symbol]

    return {
        "success": True,
        "strategy_run_id": strategy_run.id,
        "provider": runtime_state.signal_provider,
        "market_data_provider": runtime_state.kline_provider,
        "data_source": strategy_run.data_source,
        "universe_source": strategy_run.universe_source,
        "symbols_scanned": symbols_scanned,
        "signals_generated": strategy_run.signals_generated,
        "data_error_count": strategy_run.data_error_count,
        "status": strategy_run.status,
        "error": strategy_run.error,
        "spy_reference": getattr(strategy_run, "spy_reference", None),
    }


@router.get("/api/v1/signals/stale-count", response_model=StaleSignalCountResponse)
async def stale_signal_count(session: AsyncSession = Depends(get_session)):
    runtime_state = await get_runtime_state().build(session)
    stale_rows = await _load_stale_signals(session, runtime_state.trading_universe)
    local_or_mock_rows = [
        row for row in stale_rows
        if (row.data_source in STALE_LOCAL_DATA_SOURCES) or row.is_real_market_data is False
    ]
    out_of_universe_rows = [
        row for row in stale_rows
        if row.symbol not in runtime_state.trading_universe
    ]
    return StaleSignalCountResponse(
        stale_count=len(stale_rows),
        local_or_mock_count=len(local_or_mock_rows),
        out_of_universe_count=len(out_of_universe_rows),
        stale_symbols=_unique_symbols(stale_rows),
        local_or_mock_symbols=_unique_symbols(local_or_mock_rows),
        out_of_universe_symbols=_unique_symbols(out_of_universe_rows),
    )


@router.delete("/api/v1/signals/stale")
async def delete_stale_signals(session: AsyncSession = Depends(get_session)):
    """Remove stale signals using the same semantics as stale-count."""
    runtime_state = await get_runtime_state().build(session)
    signals = await _load_stale_signals(session, runtime_state.trading_universe)
    count = len(signals)
    for sig in signals:
        await session.delete(sig)
    await session.commit()
    return {"success": True, "deleted_count": count}


async def _load_stale_signals(session: AsyncSession, universe: list[str]) -> list[Signal]:
    result = await session.execute(
        select(Signal).order_by(Signal.created_at.desc())
    )
    all_signals = result.scalars().all()
    universe_set = set(universe)
    stale = [
        signal
        for signal in all_signals
        if (
            signal.data_source in STALE_LOCAL_DATA_SOURCES
            or signal.is_real_market_data is False
            or signal.symbol not in universe_set
        )
        and not (
            signal.data_source in REAL_SIGNAL_DATA_SOURCES
            and signal.is_real_market_data is True
            and signal.has_error is False
            and signal.symbol in universe_set
        )
    ]
    return stale


def _unique_symbols(signals: list[Signal]) -> list[str]:
    ordered = OrderedDict[str, None]()
    for signal in signals:
        ordered.setdefault(signal.symbol, None)
    return list(ordered.keys())
