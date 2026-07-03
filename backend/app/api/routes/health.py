import time
from fastapi import APIRouter, Depends

from app.schemas.health import HealthResponse
from app.schemas.broker_health import BrokerHealthResponse
from app.core.config import settings
from app.services.broker.base import BrokerAdapter
from app.services.broker.safety import compute_broker_safety_state
from app.api.dependencies import get_broker

router = APIRouter()
_start_time = time.time()


@router.get("/api/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="0.1.0",
        broker_mode=settings.broker_mode,
        broker_connected=True,
        database_ok=True,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@router.get("/api/v1/broker/health", response_model=BrokerHealthResponse)
async def broker_health(broker: BrokerAdapter = Depends(get_broker)):
    bh = await broker.health_check()
    state = compute_broker_safety_state(bh)

    return BrokerHealthResponse(
        broker_mode=state["broker_mode"],
        connected=state["connected"],
        data_source=state["data_source"],
        account_environment=state["account_environment"],
        is_real_account_data=state["is_real_account_data"],
        is_live_trading_enabled=state["is_live_trading_enabled"],
        read_only=state["read_only"],
        opend_host=settings.moomoo_host,
        opend_port=settings.moomoo_port,
        trd_env=state["trd_env"],
        warnings=state["warnings"],
        error=state["error"],
    )
