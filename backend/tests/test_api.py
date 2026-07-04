"""Integration tests for API endpoints using TestClient."""
import json
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import init_db, create_session_factory
from sqlalchemy import select
from app.models.order import Order
from app.models.signal import Signal
from app.models.strategy_run import StrategyRun
from app.models.app_setting import AppSetting
from sqlalchemy import delete as sa_delete


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
    assert "broker_mode" in data
    assert "database_ok" in data


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
async def test_run_signals(client, monkeypatch):
    monkeypatch.setattr(settings, "broker_mode", "mock")
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


@pytest.mark.asyncio
async def test_broker_health_endpoint(client):
    resp = await client.get("/api/v1/broker/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "broker_mode" in data
    assert "connected" in data
    assert "data_source" in data
    assert "account_environment" in data
    assert "is_real_account_data" in data
    assert "is_live_trading_enabled" in data
    assert "read_only" in data
    assert isinstance(data["warnings"], list)
    assert "data_source" in data
    assert "account_environment" in data
    assert "is_real_account_data" in data
    assert "is_live_trading_enabled" in data
    assert "read_only" in data
    assert isinstance(data["warnings"], list)


@pytest.mark.asyncio
async def test_approve_order_blocked_in_read_only(client):
    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        order = Order(
            symbol="AAPL", side="BUY", order_type="LIMIT",
            quantity=10, limit_price=210.0, status="PENDING",
        )
        session.add(order)
        await session.commit()
        order_id = order.id

    resp = await client.post("/api/v1/orders/approve", json={"order_id": order_id})
    assert resp.status_code == 403
    data = resp.json()
    assert "read-only" in data["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_order_blocked_in_read_only(client):
    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        order = Order(
            symbol="AAPL", side="BUY", order_type="LIMIT",
            quantity=10, limit_price=210.0, status="PENDING",
        )
        session.add(order)
        await session.commit()
        order_id = order.id

    resp = await client.post("/api/v1/orders/cancel", json={"order_id": order_id})
    assert resp.status_code == 403
    data = resp.json()
    assert "read-only" in data["detail"].lower()


@pytest.mark.asyncio
async def test_signals_excludes_local_in_moomoo_mode(client, monkeypatch):
    """In moomoo mode, GET /signals should exclude local_generated signals by default."""
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    await init_db()
    factory = create_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        session.add(AppSetting(key="trading_universe", value=json.dumps(["AAPL"])))
        sr = StrategyRun(
            strategy_name="momentum_relative_strength",
            status="COMPLETED",
            symbols_screened=2,
            signals_generated=2,
            data_source="moomoo",
            started_at=now,
            completed_at=now,
        )
        session.add(sr)
        await session.flush()

        local_sig = Signal(
            strategy_run_id=sr.id,
            symbol="LOCAL",
            verdict="BUY_STARTER",
            total_score=80.0,
            data_source="local_generated",
            signal_date=now,
            strategy_name="momentum_relative_strength",
            is_real_market_data=False,
            is_tradeable=False,
        )
        moomoo_sig = Signal(
            strategy_run_id=sr.id,
            symbol="AAPL",
            verdict="WATCH",
            total_score=60.0,
            data_source="moomoo",
            signal_date=now,
            strategy_name="momentum_relative_strength",
            is_real_market_data=True,
            is_tradeable=False,
        )
        session.add_all([local_sig, moomoo_sig])
        await session.commit()

    # Default GET should exclude local_generated
    resp = await client.get("/api/v1/signals")
    assert resp.status_code == 200
    data = resp.json()
    symbols = {s["symbol"] for s in data}
    assert "AAPL" in symbols
    assert "LOCAL" not in symbols

    # include_local=true should include local_generated
    resp2 = await client.get("/api/v1/signals?include_local=true")
    assert resp2.status_code == 200
    data2 = resp2.json()
    symbols2 = {s["symbol"] for s in data2}
    assert "AAPL" in symbols2
    assert "LOCAL" in symbols2


@pytest.mark.asyncio
async def test_runtime_status_endpoint(client):
    """GET /api/v1/runtime/status returns the expected provider info."""
    resp = await client.get("/api/v1/runtime/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "broker_mode" in data
    assert "broker_adapter" in data
    assert "price_source_priority" in data
    assert "signal_provider" in data
    assert "signal_data_source" in data
    assert "trading_universe" in data
    assert "trading_universe_source" in data
    assert "kline_provider" in data
    assert "kline_cache_enabled" in data
    assert "mock_enabled" in data
    assert "account_environment" in data
    assert "read_only" in data


@pytest.mark.asyncio
async def test_delete_stale_signals(client):
    """DELETE /api/v1/signals/stale removes local_generated, mock, and non-real signals."""
    await init_db()
    factory = create_session_factory()
    now = datetime.now(timezone.utc)

    # Clean existing signals to get a known baseline
    async with factory() as session:
        result = await session.execute(select(Signal))
        for sig in result.scalars().all():
            await session.delete(sig)
        await session.commit()

    async with factory() as session:
        sr = StrategyRun(
            strategy_name="test",
            status="COMPLETED",
            symbols_screened=3,
            signals_generated=3,
            data_source="mock",
            started_at=now,
            completed_at=now,
        )
        session.add(sr)
        await session.flush()

        signals = [
            Signal(
                strategy_run_id=sr.id,
                symbol=f"SYM{i}",
                verdict="BUY_STARTER",
                total_score=70.0,
                data_source=ds,
                signal_date=now,
                strategy_name="test",
            )
            for i, ds in enumerate(["local_generated", "mock", "moomoo"])
        ]
        session.add_all(signals)
        await session.commit()

    resp = await client.delete("/api/v1/signals/stale")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # All 3 are stale: local_generated, mock, and moomoo with is_real_market_data=False
    assert data["deleted_count"] == 3


@pytest.mark.asyncio
async def test_stale_signal_count_detects_local_mock_and_out_of_universe(client, monkeypatch):
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    await init_db()
    factory = create_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        result = await session.execute(select(Signal))
        for sig in result.scalars().all():
            await session.delete(sig)
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        session.add(AppSetting(key="trading_universe", value=json.dumps(["AAPL", "MSFT"])))
        sr = StrategyRun(
            strategy_name="test",
            status="COMPLETED",
            symbols_screened=4,
            signals_generated=4,
            data_source="moomoo",
            started_at=now,
            completed_at=now,
        )
        session.add(sr)
        await session.flush()
        session.add_all([
            Signal(
                strategy_run_id=sr.id,
                symbol="AAPL",
                verdict="BUY_STARTER",
                total_score=80.0,
                data_source="moomoo",
                signal_date=now,
                strategy_name="test",
                is_real_market_data=True,
                has_error=False,
            ),
            Signal(
                strategy_run_id=sr.id,
                symbol="MSFT",
                verdict="WATCH",
                total_score=60.0,
                data_source="local_generated",
                signal_date=now,
                strategy_name="test",
                is_real_market_data=False,
            ),
            Signal(
                strategy_run_id=sr.id,
                symbol="NVDA",
                verdict="WATCH",
                total_score=60.0,
                data_source="moomoo",
                signal_date=now,
                strategy_name="test",
                is_real_market_data=True,
                has_error=False,
            ),
        ])
        await session.commit()

    resp = await client.get("/api/v1/signals/stale-count")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale_count"] == 2
    assert data["local_or_mock_count"] == 1
    assert data["out_of_universe_count"] == 1
    assert set(data["stale_symbols"]) == {"MSFT", "NVDA"}
    assert data["local_or_mock_symbols"] == ["MSFT"]
    assert data["out_of_universe_symbols"] == ["NVDA"]


@pytest.mark.asyncio
async def test_stale_signal_count_does_not_count_current_universe_real_rows(client, monkeypatch):
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    await init_db()
    factory = create_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        result = await session.execute(select(Signal))
        for sig in result.scalars().all():
            await session.delete(sig)
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        session.add(AppSetting(key="trading_universe", value=json.dumps(["AAPL"])))
        sr = StrategyRun(
            strategy_name="test",
            status="COMPLETED",
            symbols_screened=1,
            signals_generated=1,
            data_source="moomoo",
            started_at=now,
            completed_at=now,
        )
        session.add(sr)
        await session.flush()
        session.add(
            Signal(
                strategy_run_id=sr.id,
                symbol="AAPL",
                verdict="BUY_STARTER",
                total_score=80.0,
                data_source="moomoo",
                signal_date=now,
                strategy_name="test",
                is_real_market_data=True,
                has_error=False,
            )
        )
        await session.commit()

    resp = await client.get("/api/v1/signals/stale-count")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale_count"] == 0
    assert data["local_or_mock_count"] == 0
    assert data["out_of_universe_count"] == 0
    assert data["stale_symbols"] == []


@pytest.mark.asyncio
async def test_delete_stale_matches_stale_count(client, monkeypatch):
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    await init_db()
    factory = create_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        result = await session.execute(select(Signal))
        for sig in result.scalars().all():
            await session.delete(sig)
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        session.add(AppSetting(key="trading_universe", value=json.dumps(["AAPL", "MSFT"])))
        sr = StrategyRun(
            strategy_name="test",
            status="COMPLETED",
            symbols_screened=4,
            signals_generated=4,
            data_source="moomoo",
            started_at=now,
            completed_at=now,
        )
        session.add(sr)
        await session.flush()
        session.add_all([
            Signal(
                strategy_run_id=sr.id,
                symbol="AAPL",
                verdict="BUY_STARTER",
                total_score=80.0,
                data_source="moomoo",
                signal_date=now,
                strategy_name="test",
                is_real_market_data=True,
                has_error=False,
            ),
            Signal(
                strategy_run_id=sr.id,
                symbol="MSFT",
                verdict="WATCH",
                total_score=60.0,
                data_source="mock",
                signal_date=now,
                strategy_name="test",
                is_real_market_data=False,
            ),
            Signal(
                strategy_run_id=sr.id,
                symbol="NVDA",
                verdict="WATCH",
                total_score=60.0,
                data_source="moomoo",
                signal_date=now,
                strategy_name="test",
                is_real_market_data=True,
                has_error=False,
            ),
        ])
        await session.commit()

    count_resp = await client.get("/api/v1/signals/stale-count")
    assert count_resp.status_code == 200
    count_data = count_resp.json()
    delete_resp = await client.delete("/api/v1/signals/stale")
    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert delete_data["deleted_count"] == count_data["stale_count"] == 2

    post_count_resp = await client.get("/api/v1/signals/stale-count")
    assert post_count_resp.status_code == 200
    post_count = post_count_resp.json()
    assert post_count["stale_count"] == 0


@pytest.mark.asyncio
async def test_run_signals_response_enriched(client, monkeypatch):
    """POST /signals/run response includes provider, data_source, universe_source, etc."""
    monkeypatch.setattr(settings, "broker_mode", "mock")
    await init_db()
    resp = await client.post("/api/v1/signals/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "strategy_run_id" in data
    assert "provider" in data
    assert "market_data_provider" in data
    assert "data_source" in data
    assert "universe_source" in data
    assert "symbols_scanned" in data
    assert "signals_generated" in data
    assert "data_error_count" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_moomoo_run_does_not_use_local_provider(client, monkeypatch):
    """When broker_mode=moomoo, POST /signals/run data_source must be 'moomoo_snapshot_plus_yfinance_kline', not 'mock'."""
    await init_db()
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    resp = await client.post("/api/v1/signals/run")
    data = resp.json()
    # Even if the run fails (no real OpenD), data_source must reflect moomoo provider
    assert data.get("data_source") == "moomoo_snapshot_plus_yfinance_kline"
    assert data.get("provider") == "MoomooMomentumResearchProvider"


@pytest.mark.asyncio
async def test_moomoo_run_does_not_generate_moomoo_symbol(client, monkeypatch):
    """broker_mode=moomoo must not generate signals for invalid broker labels like MOOMOO."""
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        await session.execute(sa_delete(Signal))
        await session.execute(sa_delete(StrategyRun))
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        session.add(AppSetting(key="trading_universe", value=json.dumps(["MOOMOO", "AAPL", "MSFT"])))
        await session.commit()

    resp = await client.post("/api/v1/signals/run")
    assert resp.status_code == 200
    data = resp.json()
    assert "MOOMOO" not in data.get("symbols_scanned", [])
    assert all(symbol in {"AAPL", "MSFT"} for symbol in data.get("symbols_scanned", []))

    factory = create_session_factory()
    async with factory() as session:
        result = await session.execute(select(Signal))
        signals = result.scalars().all()

    assert all(signal.symbol in {"AAPL", "MSFT"} for signal in signals)
    assert not any(signal.symbol == "MOOMOO" for signal in signals)


@pytest.mark.asyncio
async def test_moomoo_excludes_nonreal_outofuniverse_haserror(client, monkeypatch):
    """Moomoo GET /signals filters out non-real, out-of-universe, and has_error signals."""
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    await init_db()
    factory = create_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        # Clean up signals from previous tests
        result = await session.execute(select(Signal))
        for sig in result.scalars().all():
            await session.delete(sig)
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        session.add(AppSetting(key="trading_universe", value=json.dumps(["AAPL", "MSFT"])))
        sr = StrategyRun(
            strategy_name="test", status="COMPLETED",
            symbols_screened=6, signals_generated=6,
            data_source="moomoo", started_at=now, completed_at=now,
        )
        session.add(sr)
        await session.flush()

        signals = [
            Signal(strategy_run_id=sr.id, symbol="AAPL", verdict="BUY_STARTER",
                   total_score=80, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=True, has_error=False),  # should pass
            Signal(strategy_run_id=sr.id, symbol="MSFT", verdict="WATCH",
                   total_score=60, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=True, has_error=False),  # should pass
            Signal(strategy_run_id=sr.id, symbol="NVDA", verdict="WATCH",
                   total_score=60, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=True, has_error=False),  # out of universe
            Signal(strategy_run_id=sr.id, symbol="AAPL", verdict="WATCH",
                   total_score=60, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=False, has_error=False),  # non-real
            Signal(strategy_run_id=sr.id, symbol="AAPL", verdict="WATCH",
                   total_score=60, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=True, has_error=True),  # has error
            Signal(strategy_run_id=sr.id, symbol="MSFT", verdict="WATCH",
                   total_score=60, data_source="local_generated", signal_date=now,
                   strategy_name="test", is_real_market_data=False, has_error=False),  # local
        ]
        session.add_all(signals)
        await session.commit()

    resp = await client.get("/api/v1/signals")
    assert resp.status_code == 200
    data = resp.json()
    symbols = {s["symbol"] for s in data}
    assert symbols == {"AAPL", "MSFT"}, f"Got symbols: {symbols}"

    # With include_local=true and dedup by symbol, 3 unique symbols appear
    resp2 = await client.get("/api/v1/signals?include_local=true")
    assert resp2.status_code == 200
    data2 = resp2.json()
    symbols2 = {s["symbol"] for s in data2}
    assert symbols2 == {"AAPL", "MSFT", "NVDA"}, f"Got symbols: {symbols2}"


@pytest.mark.asyncio
async def test_market_data_status_endpoint(client):
    """GET /api/v1/market-data/status returns K-Line service metrics."""
    resp = await client.get("/api/v1/market-data/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "cache_enabled" in data
    assert "lookback_days" in data
    assert "extended_lookback_days" in data
    assert "requests" in data
    assert "cache_hits" in data
    assert "cache_misses" in data
    assert "upstream_fetches" in data
    assert "failed" in data
    assert "per_symbol" in data


@pytest.mark.asyncio
async def test_signal_pipeline_diagnostics_supports_spy_even_outside_universe(client):
    resp = await client.get("/api/v1/diagnostics/signal-pipeline?symbols=NVDA")
    assert resp.status_code == 200
    data = resp.json()
    symbol = data["symbols"][0]
    assert symbol["kline_fetch_attempted"] is True
    assert symbol["kline_bars_count"] > 0
    assert symbol["latest_bar_from_current_fetch"] is not None
    assert symbol["final_price"] is not None
    assert symbol["final_error"] is None


@pytest.mark.asyncio
async def test_signal_pipeline_diagnostics_never_500_when_provider_throws(client, api_kline_service, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulated yfinance failure")

    monkeypatch.setattr(api_kline_service._provider, "get_daily_bars", boom)

    resp = await client.get("/api/v1/diagnostics/signal-pipeline?symbols=SPY")
    assert resp.status_code == 200
    data = resp.json()
    symbol = data["symbols"][0]
    assert symbol["symbol"] == "SPY"
    assert symbol["kline_fetch_attempted"] is True
    assert symbol["kline_bars_count"] == 0
    assert symbol["final_price_source"] in {"moomoo_quote_last_price", "DATA_ERROR"}
    assert symbol["final_error"] == "simulated yfinance failure"


@pytest.mark.asyncio
async def test_signal_pipeline_diagnostics_spy_triggers_kline_fetch(client, api_kline_service):
    before = api_kline_service.requests
    resp = await client.get("/api/v1/diagnostics/signal-pipeline?symbols=SPY")
    assert resp.status_code == 200
    assert api_kline_service.requests > before
    data = resp.json()
    symbol = data["symbols"][0]
    assert symbol["symbol"] == "SPY"
    assert symbol["kline_fetch_attempted"] is True


@pytest.mark.asyncio
async def test_signal_pipeline_supports_repeated_symbols_param(client):
    resp = await client.get("/api/v1/diagnostics/signal-pipeline?symbols=SPY&symbols=NVDA")
    assert resp.status_code == 200
    data = resp.json()
    assert [row["symbol"] for row in data["symbols"]] == ["SPY", "NVDA"]


@pytest.mark.asyncio
async def test_signal_pipeline_diagnostics_spy_not_in_universe(client):
    resp = await client.get("/api/v1/diagnostics/signal-pipeline?symbols=SPY")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbols"][0]["symbol"] == "SPY"


@pytest.mark.asyncio
async def test_screener_fetches_spy_reference_before_scanning(client, api_kline_service, monkeypatch):
    call_order: list[str] = []

    async def tracked_fetch(symbol, lookback_days=None, session=None):
        call_order.append(symbol)
        dates = __import__("pandas").date_range("2024-01-01", periods=260, freq="D")
        bars = __import__("pandas").DataFrame(
            {
                "date": dates,
                "open": [100.0] * len(dates),
                "high": [101.0] * len(dates),
                "low": [99.0] * len(dates),
                "close": [100.0] * len(dates),
                "volume": [1_000_000] * len(dates),
                "adj_close": [100.0] * len(dates),
            }
        )
        return SimpleNamespace(
            bars=bars,
            cached_bars_available=False,
            cached_bar_count=len(bars),
            latest_cached_close=100.0,
            latest_cached_bar_date=dates[-1].date().isoformat(),
            fetch_attempted=True,
            fetch_failed=False,
            fetch_error=None,
            latest_bar_from_current_fetch=dates[-1].date().isoformat(),
            source="upstream",
        )

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", tracked_fetch)
    monkeypatch.setattr(__import__("app.core.config").core.config.settings, "broker_mode", "mock")
    resp = await client.post("/api/v1/signals/run")
    assert resp.status_code == 200
    assert call_order and call_order[0] == "SPY"


@pytest.mark.asyncio
async def test_spy_cache_empty_yfinance_rows_continue_screener(client, api_kline_service, monkeypatch):
    async def successful_fetch(symbol, lookback_days=None, session=None):
        import pandas as pd
        if symbol != "SPY":
            dates = pd.date_range("2024-01-01", periods=260, freq="D")
        else:
            dates = pd.date_range("2024-01-01", periods=273, freq="D")
        bars = pd.DataFrame(
            {
                "date": dates,
                "open": [100.0] * len(dates),
                "high": [101.0] * len(dates),
                "low": [99.0] * len(dates),
                "close": [100.0] * len(dates),
                "volume": [1_000_000] * len(dates),
                "adj_close": [100.0] * len(dates),
            }
        )
        return SimpleNamespace(
            bars=bars,
            cached_bars_available=False,
            cached_bar_count=len(bars),
            latest_cached_close=100.0,
            latest_cached_bar_date=dates[-1].date().isoformat(),
            fetch_attempted=True,
            fetch_failed=False,
            fetch_error=None,
            latest_bar_from_current_fetch=dates[-1].date().isoformat(),
            source="upstream",
            last_error=None,
        )

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", successful_fetch)
    monkeypatch.setattr(__import__("app.core.config").core.config.settings, "broker_mode", "moomoo")
    resp = await client.post("/api/v1/signals/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] != "FAILED"
    assert data["spy_reference"]["symbol"] == "SPY"
    assert data["spy_reference"]["kline_fetch_attempted"] is True
    assert data["spy_reference"]["upstream_fetch_attempted"] is True
    assert data["spy_reference"]["bars_after_fetch"] >= 200
    assert data["spy_reference"]["last_error"] is None


@pytest.mark.asyncio
async def test_spy_fetch_failure_returns_failed_status(client, api_kline_service, monkeypatch):
    async def failing_fetch(symbol, lookback_days=None, session=None):
        if symbol == "SPY":
            return SimpleNamespace(
                bars=__import__("pandas").DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"]),
                cached_bars_available=False,
                cached_bar_count=0,
                latest_cached_close=None,
                latest_cached_bar_date=None,
                fetch_attempted=True,
                fetch_failed=True,
                fetch_error="boom",
                latest_bar_from_current_fetch=None,
                source="upstream",
            )
        return SimpleNamespace(
            bars=__import__("pandas").DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"]),
            cached_bars_available=False,
            cached_bar_count=0,
            latest_cached_close=None,
            latest_cached_bar_date=None,
            fetch_attempted=True,
            fetch_failed=True,
            fetch_error="boom",
            latest_bar_from_current_fetch=None,
            source="upstream",
        )

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", failing_fetch)
    monkeypatch.setattr(__import__("app.core.config").core.config.settings, "broker_mode", "mock")
    resp = await client.post("/api/v1/signals/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["error"] == "SPY reference data unavailable"
    assert data["spy_reference"]["symbol"] == "SPY"
    assert data["spy_reference"]["last_error"] == "boom"


@pytest.mark.asyncio
async def test_market_data_status_includes_spy_after_diagnostics(client):
    resp = await client.get("/api/v1/diagnostics/signal-pipeline?symbols=SPY")
    assert resp.status_code == 200
    status_resp = await client.get("/api/v1/market-data/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert "SPY" in status.get("per_symbol", {})


@pytest.mark.asyncio
async def test_delete_stale_preserves_valid_moomoo_signals(client, monkeypatch):
    """DELETE /stale must NOT remove valid moomoo real signals inside the trading universe."""
    monkeypatch.setattr(settings, "broker_mode", "moomoo")
    await init_db()
    factory = create_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        # Clean up signals from previous tests
        result = await session.execute(select(Signal))
        for sig in result.scalars().all():
            await session.delete(sig)
        await session.execute(sa_delete(AppSetting).where(AppSetting.key == "trading_universe"))
        session.add(AppSetting(key="trading_universe", value=json.dumps(["AAPL"])))
        sr = StrategyRun(
            strategy_name="test", status="COMPLETED",
            symbols_screened=4, signals_generated=4,
            data_source="moomoo", started_at=now, completed_at=now,
        )
        session.add(sr)
        await session.flush()

        signals = [
            Signal(strategy_run_id=sr.id, symbol="AAPL", verdict="BUY_STARTER",
                   total_score=80, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=True, has_error=False),  # keep
            Signal(strategy_run_id=sr.id, symbol="MSFT", verdict="WATCH",
                   total_score=60, data_source="local_generated", signal_date=now,
                   strategy_name="test"),  # delete (local)
            Signal(strategy_run_id=sr.id, symbol="NVDA", verdict="WATCH",
                   total_score=60, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=False),  # delete (non-real)
            Signal(strategy_run_id=sr.id, symbol="AMZN", verdict="WATCH",
                   total_score=60, data_source="moomoo", signal_date=now,
                   strategy_name="test", is_real_market_data=True, has_error=False),  # delete (out of universe)
        ]
        session.add_all(signals)
        await session.commit()

    resp = await client.delete("/api/v1/signals/stale")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["deleted_count"] == 3

    # Verify SYM_A is still present
    async with factory() as session:
        result = await session.execute(select(Signal))
        remaining = {s.symbol for s in result.scalars().all()}
    assert remaining == {"AAPL"}
