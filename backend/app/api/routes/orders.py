from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.order import (
    OrderResponse, PreviewOrderRequest, PreviewOrderResponse,
    ApproveOrderRequest, CancelOrderRequest,
)
from app.models.order import Order
from app.db.session import get_session
from app.services.execution.order_service import preview_order, approve_order, cancel_existing_order
from app.services.broker.base import BrokerAdapter
from app.services.risk.engine import RiskEngine
from app.api.dependencies import get_broker, get_risk_engine, get_runtime_state

router = APIRouter()


@router.get("/api/v1/orders", response_model=list[OrderResponse])
async def list_orders(broker: BrokerAdapter = Depends(get_broker)):
    orders = await broker.get_open_orders()
    return [OrderResponse(
        id=o.order_id, symbol=o.symbol, side=o.side, order_type=o.order_type,
        quantity=o.quantity, filled_quantity=o.filled_quantity,
        limit_price=o.limit_price, stop_price=o.stop_price,
        status=o.status, reason=o.reason,
        risk_check_passed=None, risk_details=None,
        signal_id=None,
        created_at=o.created_at or datetime.min, submitted_at=o.submitted_at,
        filled_at=o.filled_at, cancelled_at=o.cancelled_at,
        notes=None,
    ) for o in orders]


@router.post("/api/v1/orders/preview", response_model=PreviewOrderResponse)
async def preview_order_route(
    req: PreviewOrderRequest,
    broker: BrokerAdapter = Depends(get_broker),
    risk_engine: RiskEngine = Depends(get_risk_engine),
):
    result = await preview_order(
        broker=broker,
        risk_engine=risk_engine,
        symbol=req.symbol,
        side=req.side,
        quantity=req.quantity,
        limit_price=req.limit_price,
        stop_level=req.stop_level,
    )
    return PreviewOrderResponse(**result)


@router.post("/api/v1/orders/approve")
async def approve_order_route(
    req: ApproveOrderRequest,
    broker: BrokerAdapter = Depends(get_broker),
    risk_engine: RiskEngine = Depends(get_risk_engine),
    session: AsyncSession = Depends(get_session),
):
    runtime_state = await get_runtime_state().build(session)
    if runtime_state.read_only:
        raise HTTPException(status_code=403, detail="Read-only mode: order actions are disabled.")
    result = await approve_order(
        order_id=req.order_id,
        broker=broker,
        risk_engine=risk_engine,
        session=session,
    )
    return result


@router.post("/api/v1/orders/cancel")
async def cancel_order_route(
    req: CancelOrderRequest,
    broker: BrokerAdapter = Depends(get_broker),
    session: AsyncSession = Depends(get_session),
):
    runtime_state = await get_runtime_state().build(session)
    if runtime_state.read_only:
        raise HTTPException(status_code=403, detail="Read-only mode: order actions are disabled.")
    result = await cancel_existing_order(
        order_id=req.order_id,
        broker=broker,
        session=session,
    )
    return result
