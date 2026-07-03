"""Tests for the deterministic risk engine."""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.risk.engine import RiskEngine
from app.services.broker.base import AccountSummary, QuoteDto
from tests.conftest import make_context


class TestRiskEngineKillSwitch:
    def test_kill_switch_blocks_order(self, risk_engine, sample_portfolio, sample_quote):
        risk_engine.set_kill_switch(True)
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            kill_switch=True,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is False
        assert any("kill switch" in r.lower() for r in decision.reasons)

    def test_kill_switch_disabled_allows_order(self, risk_engine, sample_portfolio, sample_quote):
        risk_engine.set_kill_switch(False)
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            kill_switch=False,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is True


class TestRiskEngineDisconnected:
    def test_disconnected_broker_blocks(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            broker_connected=False,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is False
        assert any("disconnected" in r.lower() for r in decision.reasons)


class TestRiskEngineStaleQuote:
    def test_stale_quote_blocks(self, risk_engine, sample_portfolio):
        stale_quote = QuoteDto(
            symbol="AAPL", bid=210.0, ask=210.5, last=210.25,
            volume=1000000, bid_size=500, ask_size=500,
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=30),
        )
        ctx = make_context(portfolio=sample_portfolio, quote=stale_quote)
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is False
        assert any("stale" in r.lower() for r in decision.reasons)

    def test_fresh_quote_passes(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(portfolio=sample_portfolio, quote=sample_quote)
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is True


class TestRiskEngineMissingStopLoss:
    def test_missing_stop_loss_blocks(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            stop_level=None,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is False
        assert any("stop loss" in r.lower() for r in decision.reasons)

    def test_stop_loss_present_passes(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            stop_level=200.0,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is True


class TestRiskEngineOrderType:
    def test_non_limit_order_blocked(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            order_type="MARKET",
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is False
        assert any("limit" in r.lower() for r in decision.reasons)

    def test_limit_order_passes(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            order_type="LIMIT",
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is True


class TestRiskEngineUniverse:
    def test_symbol_not_in_universe_blocked(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            symbol="PENNY",
            portfolio=sample_portfolio,
            quote=sample_quote,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is False
        assert any("universe" in r.lower() for r in decision.reasons)

    def test_symbol_in_universe_passes(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            symbol="AAPL",
            portfolio=sample_portfolio,
            quote=sample_quote,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is True


class TestRiskEngineDuplicateOrder:
    def test_duplicate_open_order_blocked(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            open_orders=[{"symbol": "AAPL", "side": "BUY", "status": "PENDING"}],
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is False
        assert any("duplicate" in r.lower() for r in decision.reasons)


class TestRiskEngineMaxQuantity:
    def test_max_quantity_computed(self, risk_engine, sample_portfolio, sample_quote):
        ctx = make_context(
            portfolio=sample_portfolio,
            quote=sample_quote,
            limit_price=200.0,
        )
        decision = risk_engine.evaluate(ctx)
        assert decision.allowed is True
        assert decision.max_allowed_quantity is not None
        assert decision.max_allowed_quantity > 0
