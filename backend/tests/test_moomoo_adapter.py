"""Tests for MoomooBrokerAdapter — read-only phase."""
import pytest
import pandas as pd
from app.services.broker.moomoo import (
    MoomooBrokerAdapter,
    MOOMOO_SDK_AVAILABLE,
    _to_moomoo_symbol,
    _from_moomoo_symbol,
    _safe_float,
)
from app.services.broker.base import AccountSummary, LimitOrderRequest


class TestSymbolMapping:
    def test_to_moomoo_symbol_basic(self):
        assert _to_moomoo_symbol("AAPL") == "US.AAPL"

    def test_to_moomoo_symbol_already_prefixed(self):
        assert _to_moomoo_symbol("US.AAPL") == "US.AAPL"

    def test_from_moomoo_symbol_basic(self):
        assert _from_moomoo_symbol("US.AAPL") == "AAPL"

    def test_from_moomoo_symbol_no_prefix(self):
        assert _from_moomoo_symbol("AAPL") == "AAPL"

    def test_roundtrip(self):
        symbols = ["AAPL", "MSFT", "NVDA", "SPY", "QQQ"]
        for s in symbols:
            assert _from_moomoo_symbol(_to_moomoo_symbol(s)) == s

    def test_fractional_position_quantity_is_preserved(self):
        assert _safe_float("0.25") == 0.25


@pytest.mark.skipif(MOOMOO_SDK_AVAILABLE, reason="SDK is installed — test requires SDK to be absent")
class TestSDKMissing:
    @pytest.mark.asyncio
    async def test_connect_returns_disconnected_when_sdk_missing(self):
        adapter = MoomooBrokerAdapter()
        await adapter.connect()
        assert adapter._connected is False
        health = await adapter.health_check()
        assert health.connected is False

    @pytest.mark.asyncio
    async def test_health_message_mentions_sdk_when_missing(self):
        adapter = MoomooBrokerAdapter()
        await adapter.connect()
        health = await adapter.health_check()
        assert health.message is not None
        assert "SDK" in health.message


class TestWriteMethodsFailClosed:
    @pytest.mark.asyncio
    async def test_place_order_raises_read_only(self):
        adapter = MoomooBrokerAdapter()
        req = LimitOrderRequest(symbol="AAPL", side="BUY", quantity=10, limit_price=210.0)
        with pytest.raises(RuntimeError) as exc:
            await adapter.place_limit_order(req)
        assert "Read-only" in str(exc.value)

    @pytest.mark.asyncio
    async def test_cancel_order_raises_read_only(self):
        adapter = MoomooBrokerAdapter()
        with pytest.raises(RuntimeError) as exc:
            await adapter.cancel_order("test")
        assert "Read-only" in str(exc.value)


class TestReadOnlyReturns:
    @pytest.mark.asyncio
    async def test_get_account_returns_empty_when_not_connected(self):
        adapter = MoomooBrokerAdapter()
        account = await adapter.get_account()
        assert account.total_value == 0.0
        assert account.cash == 0.0
        assert account.currency == "USD"

    @pytest.mark.asyncio
    async def test_get_positions_returns_empty_list_when_not_connected(self):
        adapter = MoomooBrokerAdapter()
        positions = await adapter.get_positions()
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_open_orders_returns_empty_list_when_not_connected(self):
        adapter = MoomooBrokerAdapter()
        orders = await adapter.get_open_orders()
        assert orders == []

    @pytest.mark.asyncio
    async def test_get_quote_returns_none_fields_when_not_connected(self):
        adapter = MoomooBrokerAdapter()
        quote = await adapter.get_quote("AAPL")
        assert quote.symbol == "AAPL"
        assert quote.last is None
        assert quote.bid is None
        assert quote.ask is None


@pytest.mark.asyncio
async def test_position_mapping_uses_moomoo_app_cost_and_pnl_fields(monkeypatch):
    """Moomoo's cost_price/pl_val are diluted/total P&L, not App fields."""
    from app.services.broker.moomoo import MoomooBrokerAdapter

    row = {
        "code": "US.MU",
        "qty": 4,
        "average_cost": 1007.282,
        "cost_price": 1069.35,
        "nominal_price": 913.09,
        "market_val": 3652.36,
        "unrealized_pl": -376.7667,
        "realized_pl": -248.2733,
        "pl_val": -625.04,
        "pl_ratio": -9.35,
        "today_pl_val": 190.52,
    }

    class FakeContext:
        def position_list_query(self, **kwargs):
            return 0, pd.DataFrame([row])

    adapter = MoomooBrokerAdapter()
    adapter._connected = True
    adapter._ctx = FakeContext()
    monkeypatch.setattr(adapter, "_ensure_account_id", lambda: _account_id())

    async def account():
        return AccountSummary(
            total_value=17686.0,
            cash=0.0,
            positions_value=3652.36,
            day_pnl=0.0,
            day_pnl_pct=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            drawdown_pct=0.0,
            buying_power=0.0,
        )

    async def _account_id():
        return 1

    monkeypatch.setattr(adapter, "get_account", account)
    positions = await adapter.get_positions()

    assert len(positions) == 1
    position = positions[0]
    assert position.avg_cost == 1007.28
    assert position.current_price == 913.09
    assert position.unrealized_pnl == -376.77
    assert position.realized_pnl == -248.27
    assert position.total_pnl == -625.04
    assert position.day_pnl == 190.52
