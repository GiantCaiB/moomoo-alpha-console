"""Tests for editable Trading Universe settings API."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.session import init_db
from app.models.app_setting import AppSetting
from app.core.config import settings


@pytest.fixture
def client(api_app):
    transport = ASGITransport(app=api_app)
    return AsyncClient(transport=transport, base_url="http://test")


def test_settings_parser_handles_json_array_env_value():
    parsed = Settings(universe_symbols='["QQQM","META","AMZN"]').universe_symbols
    assert parsed == ["QQQM", "META", "AMZN"]


@pytest.mark.asyncio
async def test_get_trading_universe_default(client):
    resp = await client.get("/api/v1/settings/trading-universe")
    assert resp.status_code == 200
    data = resp.json()
    assert "symbols" in data
    assert "source" in data
    assert len(data["symbols"]) > 0
    for s in data["symbols"]:
        assert s == s.upper()


@pytest.mark.asyncio
async def test_get_trading_universe_uses_env_defaults_for_legacy_db_row(client, monkeypatch):
    monkeypatch.setattr(settings, "universe_symbols", ["QQQM", "META"])
    await init_db()

    from app.db.session import create_session_factory
    factory = create_session_factory()
    async with factory() as session:
        row = await session.execute(
            __import__("sqlalchemy").select(AppSetting).where(AppSetting.key == "trading_universe")
        )
        existing = row.scalar_one_or_none()
        if existing is None:
            session.add(AppSetting(key="trading_universe", value='["SYM_A"]', description="legacy-row"))
        else:
            existing.value = '["SYM_A"]'
        await session.commit()

    resp = await client.get("/api/v1/settings/trading-universe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbols"] == ["QQQM", "META"]
    assert data["source"] == "default"


@pytest.mark.asyncio
async def test_put_trading_universe_normalizes_symbols(client):
    await init_db()
    resp = await client.put("/api/v1/settings/trading-universe", json={
        "symbols": ["aapl", "MSFT", "  nvda  ", "aapl"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbols"] == ["AAPL", "MSFT", "NVDA"]
    assert data["source"] == "database"


@pytest.mark.asyncio
async def test_put_trading_universe_persists(client):
    await init_db()
    resp = await client.put("/api/v1/settings/trading-universe", json={
        "symbols": ["AAPL", "GOOGL", "TSLA"],
    })
    assert resp.status_code == 200

    resp2 = await client.get("/api/v1/settings/trading-universe")
    data = resp2.json()
    assert data["symbols"] == ["AAPL", "GOOGL", "TSLA"]
    assert data["source"] == "database"


@pytest.mark.asyncio
async def test_put_trading_universe_empty_rejected(client):
    resp = await client.put("/api/v1/settings/trading-universe", json={
        "symbols": [],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_trading_universe_empty_after_normalization_rejected(client):
    resp = await client.put("/api/v1/settings/trading-universe", json={
        "symbols": ["  ", "", "  "],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_trading_universe_resets_to_default(client):
    """DELETE removes saved row; subsequent GET returns env defaults."""
    await init_db()
    resp = await client.put("/api/v1/settings/trading-universe", json={
        "symbols": ["CUSTOM1", "CUSTOM2"],
    })
    assert resp.status_code == 200

    resp = await client.delete("/api/v1/settings/trading-universe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    resp2 = await client.get("/api/v1/settings/trading-universe")
    data2 = resp2.json()
    assert data2["source"] == "default"
    assert len(data2["symbols"]) > 0
    assert "CUSTOM1" not in data2["symbols"]
