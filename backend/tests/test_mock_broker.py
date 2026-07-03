"""Tests for MockBrokerAdapter."""
import pytest
from app.services.broker.mock import MockBrokerAdapter
from app.services.broker.base import LimitOrderRequest


@pytest.mark.asyncio
async def test_broker_connect():
    broker = MockBrokerAdapter()
    await broker.connect()
    health = await broker.health_check()
    assert health.connected is True


@pytest.mark.asyncio
async def test_broker_get_account():
    broker = MockBrokerAdapter()
    await broker.connect()
    account = await broker.get_account()
    assert account.total_value > 0
    assert account.cash > 0
    assert account.currency == "USD"


@pytest.mark.asyncio
async def test_broker_get_positions():
    broker = MockBrokerAdapter()
    await broker.connect()
    positions = await broker.get_positions()
    assert len(positions) > 0
    for pos in positions:
        assert pos.symbol
        assert pos.quantity > 0
        assert pos.avg_cost > 0


@pytest.mark.asyncio
async def test_broker_place_limit_order():
    broker = MockBrokerAdapter()
    await broker.connect()
    req = LimitOrderRequest(symbol="AAPL", side="BUY", quantity=10, limit_price=210.0)
    order = await broker.place_limit_order(req)
    assert order.order_id
    assert order.status in ("SUBMITTED",)
    assert order.symbol == "AAPL"
    assert order.quantity == 10


@pytest.mark.asyncio
async def test_broker_cancel_order():
    broker = MockBrokerAdapter()
    await broker.connect()
    req = LimitOrderRequest(symbol="AAPL", side="BUY", quantity=10, limit_price=210.0)
    order = await broker.place_limit_order(req)
    await broker.cancel_order(order.order_id)
    open_orders = await broker.get_open_orders()
    assert all(o.order_id != order.order_id for o in open_orders)
