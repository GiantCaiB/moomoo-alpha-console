from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_broker, get_kline_service, get_price_resolver
from app.db.session import get_session
from app.models.position_lifecycle_state import PositionLifecycleState
from app.schemas.position_management import PositionManagementSignalResponse, PositionSignalRunResponse
from app.services.position_management.profit_tail import ProfitTailStrategyService

router = APIRouter(tags=["position-signals"])


def _service() -> ProfitTailStrategyService:
    return ProfitTailStrategyService(
        broker=get_broker(),
        kline_service=get_kline_service(),
        price_resolver=get_price_resolver(),
    )


@router.post("/api/v1/position-signals/run", response_model=PositionSignalRunResponse)
async def run_position_signals(session: AsyncSession = Depends(get_session)):
    service = _service()
    try:
        _, summary = await service.run(session)
        return PositionSignalRunResponse(**summary)
    except Exception as exc:
        await session.rollback()
        return PositionSignalRunResponse(
            status="FAILED",
            positions_scanned=0,
            signals_generated=0,
            data_error_count=0,
            read_only=True,
            error=str(exc),
        )


@router.get("/api/v1/position-signals", response_model=list[PositionManagementSignalResponse])
async def list_position_signals(
    include_history: bool = False,
    session: AsyncSession = Depends(get_session),
):
    service = _service()
    signal_rows = await service.list_signals(session, include_history=include_history)
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
            )
        )
    return responses
