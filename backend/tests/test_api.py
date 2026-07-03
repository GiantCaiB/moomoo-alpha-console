"""Integration tests for API endpoints using TestClient."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import init_db


@pytest.fixture
def client(api_app):
    transport = ASGITransport(app=api_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["broker_mode"] == "mock"


@pytest.mark.asyncio
async def test_config_endpoint(client):
    resp = await client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "broker_mode" in data
    assert "universe_symbols" in data


@pytest.mark.asyncio
async def test_watchlist_endpoint(client):
    resp = await client.get("/api/v1/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_signals_endpoint(client):
    resp = await client.get("/api/v1/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_run_signals(client):
    await init_db()
    resp = await client.post("/api/v1/signals/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_risk_status_endpoint(client):
    resp = await client.get("/api/v1/risk/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "kill_switch_enabled" in data


@pytest.mark.asyncio
async def test_kill_switch(client):
    resp = await client.post("/api/v1/risk/kill-switch", json={"enabled": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["kill_switch_enabled"] is True

    resp = await client.post("/api/v1/risk/kill-switch", json={"enabled": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["kill_switch_enabled"] is False


@pytest.mark.asyncio
async def test_order_preview(client):
    resp = await client.post("/api/v1/orders/preview", json={
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "limit_price": 210.0,
        "stop_level": 200.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "allowed" in data
    assert "reasons" in data


@pytest.mark.asyncio
async def test_order_preview_blocked_when_kill_switch(client):
    await client.post("/api/v1/risk/kill-switch", json={"enabled": True})
    resp = await client.post("/api/v1/orders/preview", json={
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "limit_price": 210.0,
        "stop_level": 200.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    await client.post("/api/v1/risk/kill-switch", json={"enabled": False})
