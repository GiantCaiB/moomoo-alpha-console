import time
from fastapi import APIRouter, Depends

from app.schemas.health import HealthResponse
from app.core.config import settings

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
