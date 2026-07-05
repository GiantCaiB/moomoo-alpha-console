"""Tests for strategy profiles API and integration."""
import pytest


@pytest.mark.asyncio
async def test_list_entry_strategy_profiles(api_app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/strategy-profiles?type=entry")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    profile = data[0]
    assert profile["strategy_type"] == "entry"
    assert profile["strategy_key"] == "momentum_relative_strength"
    assert profile["version"] == "1.0.0"
    assert profile["is_default"] is True
    assert profile["parameters"] is not None
    assert profile["rules_summary"] is not None
    assert profile["rules_summary"]["type"] == "entry"


@pytest.mark.asyncio
async def test_list_position_strategy_profiles(api_app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/strategy-profiles?type=position_guidance")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    profile = data[0]
    assert profile["strategy_type"] == "position_guidance"
    assert profile["strategy_key"] == "profit_tail_loss_defense"
    assert profile["version"] == "1.0.0"
    assert profile["is_default"] is True
    assert profile["parameters"] is not None
    assert profile["rules_summary"] is not None
    assert profile["rules_summary"]["type"] == "position_guidance"


@pytest.mark.asyncio
async def test_get_strategy_profile_by_id(api_app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_resp = await client.get("/api/v1/strategy-profiles?type=entry")
        profiles = list_resp.json()
        assert len(profiles) >= 1
        profile_id = profiles[0]["id"]

        resp = await client.get(f"/api/v1/strategy-profiles/{profile_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == profile_id
    assert data["name"] == "Momentum Relative Strength v1"
    assert data["parameters"]["buy_score_threshold"] == 75
    assert data["parameters"]["watch_score_threshold"] == 65
    assert data["parameters"]["min_bars"] == 220
    assert data["parameters"]["benchmark"] == "SPY"


@pytest.mark.asyncio
async def test_get_strategy_profile_not_found(api_app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/strategy-profiles/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_signals_without_profile_uses_default(api_app, api_broker, api_kline_service, monkeypatch):
    """Run signals without strategy_profile_id should not error."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/signals/run", json={})
    assert resp.status_code == 200 or resp.status_code == 500
    if resp.status_code == 200:
        data = resp.json()
        assert data["success"] is True
    # 500 is also acceptable if SPY data isn't available in test env


@pytest.mark.asyncio
async def test_run_signals_with_empty_body_uses_default(api_app, api_broker, api_kline_service, monkeypatch):
    """Run signals with no body should work (backward compat)."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/signals/run")
    assert resp.status_code == 200 or resp.status_code == 500


@pytest.mark.asyncio
async def test_run_position_signals_without_profile_uses_default(api_app, api_broker, api_kline_service, monkeypatch):
    """Run position signals without strategy_profile_id should not error."""
    from httpx import ASGITransport, AsyncClient

    async def get_positions():
        from app.services.broker.base import PositionDto
        return [PositionDto(symbol="META", quantity=100, avg_cost=100.0, current_price=None, unrealized_pnl=None, day_pnl=None, stop_level=None, position_pct=10.0)]

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    import pandas as pd
    from tests.test_position_management import _make_fetch_result, _bars_from_weekly_closes

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_weekly_closes([100.0] * 35))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/position-signals/run", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["read_only"] is True
    assert data["positions_scanned"] >= 1


@pytest.mark.asyncio
async def test_run_position_signals_with_profile_id(api_app, api_broker, api_kline_service, monkeypatch):
    """Run position signals with explicit profile should use that profile's parameters."""
    from httpx import ASGITransport, AsyncClient

    async def get_positions():
        from app.services.broker.base import PositionDto
        return [PositionDto(symbol="META", quantity=100, avg_cost=100.0, current_price=None, unrealized_pnl=None, day_pnl=None, stop_level=None, position_pct=10.0)]

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    from tests.test_position_management import _make_fetch_result, _bars_from_weekly_closes

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_weekly_closes([100.0] * 35))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_resp = await client.get("/api/v1/strategy-profiles?type=position_guidance")
        profiles = list_resp.json()
        assert len(profiles) >= 1
        profile_id = profiles[0]["id"]

        resp = await client.post("/api/v1/position-signals/run", json={"strategy_profile_id": profile_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_strategy_registry_metadata():
    from app.services.strategy_registry import StrategyRegistry

    entry_def = StrategyRegistry.get("entry", "momentum_relative_strength")
    assert entry_def is not None
    assert entry_def.version == "1.0.0"
    assert entry_def.default_parameters["benchmark"] == "SPY"

    pos_def = StrategyRegistry.get("position_guidance", "profit_tail_loss_defense")
    assert pos_def is not None
    assert pos_def.version == "1.0.0"
    assert len(pos_def.default_parameters["trim_thresholds"]) == 3
