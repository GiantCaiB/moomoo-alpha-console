from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.schemas.risk import RiskStatusResponse, KillSwitchRequest
from app.models.risk_event import RiskEvent
from app.db.session import get_session
from app.services.risk.engine import RiskEngine
from app.services.broker.base import BrokerAdapter
from app.services.broker.safety import compute_broker_safety_state
from app.api.dependencies import get_risk_engine, get_broker

router = APIRouter()

RECENT_EVENT_LIMIT = 20


@router.get("/api/v1/risk/status", response_model=RiskStatusResponse)
async def risk_status(
    risk_engine: RiskEngine = Depends(get_risk_engine),
    broker: BrokerAdapter = Depends(get_broker),
    session: AsyncSession = Depends(get_session),
):
    account = await broker.get_account()
    bh = await broker.health_check()
    safety = compute_broker_safety_state(bh)

    recent_events_result = await session.execute(
        select(RiskEvent).order_by(desc(RiskEvent.event_time)).limit(RECENT_EVENT_LIMIT)
    )
    events = recent_events_result.scalars().all()

    daily_loss_pct = abs(min(account.day_pnl_pct, 0))
    dd = account.drawdown_pct

    trading_blocked = (
        risk_engine.kill_switch_enabled
        or not safety["connected"]
        or safety["read_only"]
        or not safety["is_live_trading_enabled"]
    )

    return RiskStatusResponse(
        kill_switch_enabled=risk_engine.kill_switch_enabled,
        broker_connected=safety["connected"],
        daily_loss_pct=daily_loss_pct,
        drawdown_pct=dd,
        daily_loss_limit_pct=5.0,
        max_drawdown_soft_pct=10.0,
        max_drawdown_hard_pct=20.0,
        daily_loss_exceeded=daily_loss_pct > 5.0,
        drawdown_soft_exceeded=dd > 10.0,
        drawdown_hard_exceeded=dd > 20.0,
        recent_events=[
            {"id": e.id, "event_type": e.event_type, "severity": e.severity,
             "symbol": e.symbol, "message": e.message, "blocked": e.blocked,
             "event_time": e.event_time.isoformat()}
            for e in events
        ],
        trading_blocked=trading_blocked,
    )


@router.post("/api/v1/risk/kill-switch")
async def toggle_kill_switch(
    req: KillSwitchRequest,
    risk_engine: RiskEngine = Depends(get_risk_engine),
):
    risk_engine.set_kill_switch(req.enabled)
    return {"success": True, "kill_switch_enabled": req.enabled}
