"""
Order execution service.

Handles the full order lifecycle:
  1. preview  → risk check → return decision
  2. approve  → risk check → submit to broker → log
  3. cancel   → broker cancel → log
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.order import Order
from app.services.broker.base import (
    BrokerAdapter,
    LimitOrderRequest,
    OrderDto,
)
from app.services.risk.engine import RiskEngine, OrderCheckContext
from app.services.audit.service import log_action

logger = logging.getLogger(__name__)


async def preview_order(
    broker: BrokerAdapter,
    risk_engine: RiskEngine,
    symbol: str,
    side: str,
    quantity: int,
    limit_price: float,
    stop_level: float | None,
) -> dict:
    account = await broker.get_account()
    quote = await broker.get_quote(symbol)
    positions_dtos = await broker.get_positions()
    open_order_dtos = await broker.get_open_orders()

    ctx = OrderCheckContext(
        symbol=symbol,
        side=side,
        order_type="LIMIT",
        quantity=quantity,
        limit_price=limit_price,
        stop_level=stop_level,
        portfolio=account,
        quote=quote,
        positions=[{"symbol": p.symbol, "quantity": p.quantity, "current_price": p.current_price} for p in positions_dtos],
        open_orders=[{"symbol": o.symbol, "side": o.side, "status": o.status} for o in open_order_dtos],
        daily_loss_pct=abs(min(account.day_pnl_pct, 0)),
        drawdown_pct=account.drawdown_pct,
        kill_switch_enabled=risk_engine.kill_switch_enabled,
        broker_connected=True,
        strategy_run_id=None,
    )

    decision = risk_engine.evaluate(ctx)
    return {
        "allowed": decision.allowed,
        "reasons": decision.reasons,
        "warnings": decision.warnings,
        "max_allowed_quantity": decision.max_allowed_quantity,
    }


async def approve_order(
    order_id: str,
    broker: BrokerAdapter,
    risk_engine: RiskEngine,
    session: AsyncSession,
) -> dict:
    order = await session.get(Order, order_id)
    if not order:
        return {"success": False, "error": "Order not found"}

    if order.status != "PENDING":
        return {"success": False, "error": f"Order status is {order.status}, not PENDING"}

    account = await broker.get_account()
    quote = await broker.get_quote(order.symbol)
    positions_dtos = await broker.get_positions()
    open_order_dtos = await broker.get_open_orders()

    ctx = OrderCheckContext(
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        limit_price=order.limit_price or 0,
        stop_level=order.stop_price,
        portfolio=account,
        quote=quote,
        positions=[{"symbol": p.symbol, "quantity": p.quantity, "current_price": p.current_price} for p in positions_dtos],
        open_orders=[{"symbol": o.symbol, "side": o.side, "status": o.status} for o in open_order_dtos],
        daily_loss_pct=abs(min(account.day_pnl_pct, 0)),
        drawdown_pct=account.drawdown_pct,
        kill_switch_enabled=risk_engine.kill_switch_enabled,
        broker_connected=True,
        strategy_run_id=order.signal_id,
    )

    decision = risk_engine.evaluate(ctx)
    order.risk_check_passed = decision.allowed
    order.risk_details = json.dumps({"reasons": decision.reasons, "warnings": decision.warnings})

    if not decision.allowed:
        order.status = "REJECTED"
        order.reason = "; ".join(decision.reasons)
        await session.commit()
        await log_action(session, "ORDER_REJECTED", "Order", order.id, order.risk_details)
        return {"success": False, "error": "; ".join(decision.reasons), "decision": decision}

    broker_request = LimitOrderRequest(
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        limit_price=order.limit_price or 0,
        stop_level=order.stop_price,
        reason=order.reason,
    )

    try:
        broker_order: OrderDto = await broker.place_limit_order(broker_request)
        order.status = "SUBMITTED"
        order.broker_order_id = broker_order.order_id
        order.submitted_at = datetime.now(timezone.utc)
        await session.commit()

        await log_action(session, "ORDER_APPROVED", "Order", order.id, json.dumps({
            "broker_order_id": broker_order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "qty": order.quantity,
            "price": order.limit_price,
        }))
        return {"success": True, "order_id": order.id, "broker_order_id": broker_order.order_id}
    except Exception as e:
        order.status = "FAILED"
        order.reason = str(e)
        await session.commit()
        await log_action(session, "ORDER_FAILED", "Order", order.id, str(e))
        return {"success": False, "error": str(e)}


async def cancel_existing_order(
    order_id: str,
    broker: BrokerAdapter,
    session: AsyncSession,
) -> dict:
    order = await session.get(Order, order_id)
    if not order:
        return {"success": False, "error": "Order not found"}
    if order.status in ("FILLED", "CANCELLED"):
        return {"success": False, "error": f"Cannot cancel order with status {order.status}"}

    try:
        if order.broker_order_id:
            await broker.cancel_order(order.broker_order_id)
        order.status = "CANCELLED"
        order.cancelled_at = datetime.now(timezone.utc)
        await session.commit()
        await log_action(session, "ORDER_CANCELLED", "Order", order.id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
