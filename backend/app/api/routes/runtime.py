from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_runtime_state
from app.db.session import get_session

router = APIRouter()


@router.get("/api/v1/runtime/status")
async def runtime_status(session: AsyncSession = Depends(get_session)):
    runtime_state = await get_runtime_state().build(session)
    return {
        "broker_mode": runtime_state.broker_mode,
        "broker_adapter": runtime_state.broker_adapter,
        "account_environment": runtime_state.account_environment,
        "trading_universe": runtime_state.trading_universe,
        "trading_universe_source": runtime_state.trading_universe_source,
        "kline_provider": runtime_state.kline_provider,
        "kline_cache_enabled": runtime_state.kline_cache_enabled,
        "signal_provider": runtime_state.signal_provider,
        "signal_data_source": runtime_state.signal_data_source,
        "price_source_priority": runtime_state.price_source_priority,
        "mock_enabled": runtime_state.mock_enabled,
        "read_only": runtime_state.read_only,
    }
