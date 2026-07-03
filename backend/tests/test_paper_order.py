"""Tests for paper broker order flow."""
import pytest
from app.services.broker.paper import PaperBrokerAdapter
from app.services.broker.base import LimitOrderRequest


@pytest.mark.asyncio
async def test_paper_broker_place_and_cancel():
    broker = PaperBrokerAdapter()
    await broker.connect()

    req = LimitOrderRequest(symbol="AAPL", side="BUY", quantity=10, limit_price=210.0, stop_level=200.0)
    order = await broker.place_limit_order(req)
    assert order.order_id
    assert order.status == "SUBMITTED"

    await broker.cancel_order(order.order_id)
    open_orders = await broker.get_open_orders()
    assert all(o.order_id != order.order_id for o in open_orders)


@pytest.mark.asyncio
async def test_paper_broker_trade_log():
    broker = PaperBrokerAdapter()
    await broker.connect()

    await broker.place_limit_order(
        LimitOrderRequest(symbol="AAPL", side="BUY", quantity=10, limit_price=210.0)
    )
    log = broker.get_trade_log()
    assert len(log) == 1
    assert log[0]["action"] == "PLACE_LIMIT"
    assert log[0]["symbol"] == "AAPL"
