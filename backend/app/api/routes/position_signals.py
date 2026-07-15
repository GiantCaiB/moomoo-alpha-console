import json
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_broker, get_kline_service, get_price_resolver
from app.db.session import get_session
from app.models.position_lifecycle_state import PositionLifecycleState
from app.models.position_management_signal import PositionManagementSignal
from app.models.strategy_profile import StrategyProfile
from app.models.position_guidance_run import PositionGuidanceRun
from app.schemas.position_management import PositionGuidanceRunResponse, PositionManagementSignalResponse, PositionSignalRunResponse
from app.services.position_management.profit_tail import ProfitTailStrategyService

logger = logging.getLogger(__name__)


class RunPositionSignalsRequest(BaseModel):
    strategy_profile_id: str | None = None


class DeleteStalePositionSignalsResponse(BaseModel):
    success: bool
    deleted_count: int = 0
    deleted_symbols: list[str] = []
    active_symbols: list[str] = []


router = APIRouter(tags=["position-signals"])


def _service(
    strategy_profile_id: str | None = None,
    strategy_version: str | None = None,
    parameters: dict | None = None,
) -> ProfitTailStrategyService:
    return ProfitTailStrategyService(
        broker=get_broker(),
        kline_service=get_kline_service(),
        price_resolver=get_price_resolver(),
        strategy_profile_id=strategy_profile_id,
        strategy_version=strategy_version,
        parameters=parameters,
    )


@router.post("/api/v1/position-signals/run", response_model=PositionSignalRunResponse)
async def run_position_signals(
    req: RunPositionSignalsRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    strategy_profile_id = None
    strategy_version = None
    parameters = None

    run = PositionGuidanceRun(
        strategy_name="profit_tail_loss_defense",
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.flush()

    if req and req.strategy_profile_id:
        result = await session.execute(
            select(StrategyProfile).where(StrategyProfile.id == req.strategy_profile_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            run.status = "FAILED"
            run.error_message = f"Strategy profile {req.strategy_profile_id} not found"
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
            return PositionSignalRunResponse(
                id=run.id,
                status="FAILED",
                positions_scanned=0,
                signals_generated=0,
                data_error_count=0,
                read_only=True,
                error=f"Strategy profile {req.strategy_profile_id} not found",
                started_at=run.started_at,
                finished_at=run.finished_at,
            )
        strategy_profile_id = profile.id
        strategy_version = profile.version
        parameters = json.loads(profile.parameters_json) if profile.parameters_json else {}
        run.strategy_profile_id = profile.id
        run.strategy_version = profile.version

    run.parameters_snapshot_json = json.dumps(parameters or {})

    service = _service(
        strategy_profile_id=strategy_profile_id,
        strategy_version=strategy_version,
        parameters=parameters,
    )
    try:
        _, summary = await service.run(session, run)
        return PositionSignalRunResponse(**summary)
    except Exception as exc:
        logger.exception("Position guidance run failed: %s", exc)
        await session.rollback()
        run.status = "FAILED"
        run.error_message = f"Position guidance run failed: {exc}"
        run.finished_at = datetime.now(timezone.utc)
        session.add(run)
        await session.commit()
        return PositionSignalRunResponse(
            id=run.id,
            status="FAILED",
            positions_scanned=0,
            signals_generated=0,
            data_error_count=0,
            read_only=True,
            error=f"Position guidance run failed: {exc}",
            started_at=run.started_at,
            finished_at=run.finished_at,
        )


@router.get("/api/v1/position-signals/runs", response_model=list[PositionGuidanceRunResponse])
async def list_position_guidance_runs(limit: int = 10, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(PositionGuidanceRun)
        .order_by(PositionGuidanceRun.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    return result.scalars().all()


@router.get("/api/v1/position-signals/runs/{run_id}", response_model=PositionGuidanceRunResponse)
async def get_position_guidance_run(run_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(PositionGuidanceRun).where(PositionGuidanceRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Position Guidance run not found")
    return run


@router.get("/api/v1/position-signals", response_model=list[PositionManagementSignalResponse])
async def list_position_signals(
    include_history: bool = False,
    include_inactive: bool = Query(False, alias="include_inactive"),
    session: AsyncSession = Depends(get_session),
):
    service = _service()

    active_symbols: set[str] | None = None
    if not include_inactive:
        try:
            positions = await get_broker().get_positions()
            active_symbols = {p.symbol.upper().strip() for p in positions if (p.quantity or 0) > 0}
        except Exception as exc:
            logger.error("Failed to fetch broker positions for position-signals filter: %s", exc)
            return []

    signal_rows = await service.list_signals(session, include_history=include_history, active_symbols=active_symbols)
    state_result = await session.execute(select(PositionLifecycleState))
    states = {state.symbol: state for state in state_result.scalars().all()}
    responses: list[PositionManagementSignalResponse] = []
    for row in signal_rows:
        state = states.get(row.symbol)
        responses.append(
            PositionManagementSignalResponse(
                id=None,
                symbol=row.symbol,
                signal=row.signal,
                reason=row.reason,
                current_price=row.current_price,
                avg_cost=row.avg_cost,
                quantity=row.quantity,
                gain_pct=row.gain_pct,
                suggested_action=row.suggested_action,
                suggested_quantity=row.suggested_quantity,
                suggested_trim_pct=row.suggested_trim_pct,
                tail_mode=row.tail_mode,
                weekly_close=row.weekly_close,
                weekly_sma20=row.weekly_sma20,
                weekly_sma30=row.weekly_sma30,
                drawdown_from_high=row.drawdown_from_high,
                original_cost_basis=state.original_cost_basis if state else row.original_cost_basis,
                highest_price_since_entry=state.highest_price_since_entry if state else row.highest_price_since_entry,
                tail_started_at=state.tail_started_at if state else None,
                trim_25_done=state.trim_25_done if state else None,
                trim_50_done=state.trim_50_done if state else None,
                trim_75_done=state.trim_75_done if state else None,
                data_source=row.data_source,
                price_source=row.price_source,
                bar_source=row.bar_source,
                is_real_market_data=row.is_real_market_data,
                generated_at=row.generated_at,
                created_at=row.generated_at,
                run_id=row.run_id,
                strategy_profile_id=row.strategy_profile_id,
                strategy_version=row.strategy_version,
            )
        )
    return responses


@router.delete("/api/v1/position-signals/stale", response_model=DeleteStalePositionSignalsResponse)
async def delete_stale_position_signals(
    dry_run: bool = Query(False, alias="dry_run"),
    session: AsyncSession = Depends(get_session),
):
    try:
        positions = await get_broker().get_positions()
        active_symbols = {p.symbol.upper().strip() for p in positions if (p.quantity or 0) > 0}
    except Exception as exc:
        logger.error("Failed to fetch broker positions for stale cleanup: %s", exc)
        return DeleteStalePositionSignalsResponse(
            success=False,
            deleted_count=0,
            deleted_symbols=[],
            active_symbols=[],
        )

    result = await session.execute(select(PositionManagementSignal))
    all_signals = result.scalars().all()

    stale = [s for s in all_signals if s.symbol.upper().strip() not in active_symbols]
    deleted_symbols = sorted({s.symbol for s in stale})

    if not dry_run:
        for sig in stale:
            await session.delete(sig)
        await session.commit()

    return DeleteStalePositionSignalsResponse(
        success=True,
        deleted_count=len(stale),
        deleted_symbols=deleted_symbols,
        active_symbols=sorted(active_symbols),
    )
