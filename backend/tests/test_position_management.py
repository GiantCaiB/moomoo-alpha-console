from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from sqlalchemy import delete as sa_delete

from app.db.session import init_db
from app.models.position_lifecycle_state import PositionLifecycleState
from app.models.position_management_signal import PositionManagementSignal
from app.services.broker.base import PositionDto, QuoteDto


def _bars_from_weekly_closes(weekly_closes: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-01", periods=len(weekly_closes) * 5)
    closes = [close for close in weekly_closes for _ in range(5)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [value * 1.01 for value in closes],
            "low": [value * 0.99 for value in closes],
            "close": closes,
            "volume": [1_000_000] * len(closes),
            "adj_close": closes,
        }
    )


def _bars_from_daily_closes(daily_closes: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-01", periods=len(daily_closes))
    return pd.DataFrame(
        {
            "date": dates,
            "open": daily_closes,
            "high": [value * 1.01 for value in daily_closes],
            "low": [value * 0.99 for value in daily_closes],
            "close": daily_closes,
            "volume": [1_000_000] * len(daily_closes),
            "adj_close": daily_closes,
        }
    )


def _make_fetch_result(bars: pd.DataFrame, fetch_error: str | None = None):
    latest_close = float(bars["close"].iloc[-1]) if not bars.empty else None
    latest_date = bars["date"].iloc[-1].date().isoformat() if not bars.empty else None
    return SimpleNamespace(
        bars=bars,
        cached_bars_available=not bars.empty,
        cached_bar_count=len(bars),
        latest_cached_close=latest_close,
        latest_cached_bar_date=latest_date,
        fetch_attempted=True,
        fetch_failed=bars.empty,
        fetch_error=fetch_error,
        latest_bar_from_current_fetch=latest_date,
        source="upstream" if fetch_error is None else "upstream",
        last_error=fetch_error,
    )


class FakePositionBroker:
    def __init__(self, positions: list[PositionDto], quote_last: float | None = None):
        self._positions = positions
        self._quote_last = quote_last
        self.place_limit_order_calls = 0
        self.cancel_order_calls = 0

    async def get_positions(self):
        return self._positions

    async def get_quote(self, symbol: str):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=self._quote_last,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    async def place_limit_order(self, request):
        self.place_limit_order_calls += 1
        raise AssertionError("Position signals must not place orders")

    async def cancel_order(self, order_id: str):
        self.cancel_order_calls += 1
        raise AssertionError("Position signals must not cancel orders")


@pytest.fixture
def position_signals_client(api_app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=api_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
async def clear_position_signal_tables():
    await init_db()
    from app.db.session import create_session_factory

    factory = create_session_factory()
    async with factory() as session:
        await session.execute(sa_delete(PositionManagementSignal))
        await session.execute(sa_delete(PositionLifecycleState))
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "gain_pct,expected_signal,expected_trim_pct",
    [
        (10, "HOLD", None),
        (25, "TRIM_PROFIT", 10),
        (50, "TRIM_PROFIT", 15),
        (75, "TRIM_PROFIT", 20),
        (100, "ENTER_TAIL_MODE", None),
    ],
)
async def test_position_signals_gain_thresholds(position_signals_client, api_broker, api_kline_service, monkeypatch, gain_pct, expected_signal, expected_trim_pct):
    await init_db()
    current_price = 100.0 + gain_pct
    position = PositionDto(
        symbol="META",
        quantity=100,
        avg_cost=100.0,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=10.0,
    )
    async def get_positions():
        return [position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)
    api_broker.place_limit_order_calls = 0
    api_broker.cancel_order_calls = 0

    async def place_limit_order(request):
        api_broker.place_limit_order_calls += 1
        return None

    async def cancel_order(order_id):
        api_broker.cancel_order_calls += 1
        return None

    monkeypatch.setattr(api_broker, "place_limit_order", place_limit_order)
    monkeypatch.setattr(api_broker, "cancel_order", cancel_order)
    api_broker.place_limit_order_calls = 0
    api_broker.cancel_order_calls = 0

    async def place_limit_order(request):
        api_broker.place_limit_order_calls += 1
        return None

    async def cancel_order(order_id):
        api_broker.cancel_order_calls += 1
        return None

    monkeypatch.setattr(api_broker, "place_limit_order", place_limit_order)
    monkeypatch.setattr(api_broker, "cancel_order", cancel_order)
    api_broker.place_limit_order_calls = 0
    api_broker.cancel_order_calls = 0

    async def place_limit_order(request):
        api_broker.place_limit_order_calls += 1
        return None

    async def cancel_order(order_id):
        api_broker.cancel_order_calls += 1
        return None

    monkeypatch.setattr(api_broker, "place_limit_order", place_limit_order)
    monkeypatch.setattr(api_broker, "cancel_order", cancel_order)
    bars = _bars_from_weekly_closes([current_price] * 35)

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(bars)

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["read_only"] is True
    assert data["positions_scanned"] == 1
    assert data["signals_generated"] == 1
    assert data["data_error_count"] == 0

    rows = (await position_signals_client.get("/api/v1/position-signals")).json()
    row = rows[0]
    assert row["symbol"] == "META"
    assert row["signal"] == expected_signal
    if expected_trim_pct is None:
        assert row["suggested_trim_pct"] is None
    else:
        assert row["suggested_trim_pct"] == expected_trim_pct


@pytest.mark.asyncio
async def test_position_signals_tail_modes(position_signals_client, api_broker, api_kline_service, monkeypatch):
    await init_db()
    broker_position = PositionDto(
        symbol="AAPL",
        quantity=100,
        avg_cost=100.0,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=10.0,
    )
    async def get_positions():
        return [broker_position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_weekly_closes([100.0] * 35))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    from app.db.session import create_session_factory

    factory = create_session_factory()
    async with factory() as session:
        session.add(
            PositionLifecycleState(
                symbol="AAPL",
                original_entry_price=100.0,
                original_quantity=100,
                original_cost_basis=10000.0,
                highest_price_since_entry=120.0,
                trim_25_done=False,
                trim_50_done=False,
                trim_75_done=False,
                tail_mode=True,
                tail_started_at=datetime.now(timezone.utc),
                tail_original_quantity=100,
                notes=None,
            )
        )
        await session.commit()

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
    rows = (await position_signals_client.get("/api/v1/position-signals")).json()
    assert rows[0]["signal"] == "HOLD_TAIL"

    async def trim_fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_weekly_closes([50.0] * 10 + [100.0] * 19 + [90.0]))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", trim_fetch)
    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    rows = (await position_signals_client.get("/api/v1/position-signals?include_history=true")).json()
    assert rows[0]["signal"] == "REVIEW_POSITION"


@pytest.mark.asyncio
async def test_position_signals_exit_tail_on_breakdown(position_signals_client, api_broker, api_kline_service, monkeypatch):
    await init_db()
    position = PositionDto(
        symbol="NVDA",
        quantity=50,
        avg_cost=100.0,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=12.0,
    )
    async def get_positions():
        return [position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_weekly_closes([100.0] * 40))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    from app.db.session import create_session_factory

    factory = create_session_factory()
    async with factory() as session:
        session.add(
            PositionLifecycleState(
                symbol="NVDA",
                original_entry_price=100.0,
                original_quantity=50,
                original_cost_basis=5000.0,
                highest_price_since_entry=160.0,
                trim_25_done=False,
                trim_50_done=False,
                trim_75_done=False,
                tail_mode=True,
                tail_started_at=datetime.now(timezone.utc),
                tail_original_quantity=50,
                notes=None,
            )
        )
        await session.commit()

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    row = (await position_signals_client.get("/api/v1/position-signals")).json()[0]
    assert row["signal"] == "EXIT_POSITION"
    assert row["suggested_trim_pct"] == 100


@pytest.mark.asyncio
async def test_position_signals_data_errors_and_skip_zero_qty(position_signals_client, api_broker, api_kline_service, monkeypatch):
    await init_db()
    positions = [
        PositionDto(
            symbol="AMZN",
            quantity=0,
            avg_cost=100.0,
            current_price=None,
            unrealized_pnl=None,
            day_pnl=None,
            stop_level=None,
            position_pct=0.0,
        ),
        PositionDto(
            symbol="MSFT",
            quantity=10,
            avg_cost=None,  # type: ignore[arg-type]
            current_price=None,
            unrealized_pnl=None,
            day_pnl=None,
            stop_level=None,
            position_pct=5.0,
        ),
    ]
    async def get_positions():
        return positions

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"]), fetch_error="Insufficient weekly bars for SMA30")

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["positions_scanned"] == 1
    assert data["signals_generated"] == 1
    assert data["data_error_count"] == 1
    rows = (await position_signals_client.get("/api/v1/position-signals")).json()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "MSFT"
    assert rows[0]["signal"] == "DATA_ERROR"


@pytest.mark.asyncio
async def test_position_signals_no_order_placement(position_signals_client, api_broker, api_kline_service, monkeypatch):
    await init_db()
    position = PositionDto(
        symbol="META",
        quantity=5,
        avg_cost=100.0,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=1.0,
    )
    async def get_positions():
        return [position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)
    api_broker.place_limit_order_calls = 0
    api_broker.cancel_order_calls = 0

    async def place_limit_order(request):
        api_broker.place_limit_order_calls += 1
        return None

    async def cancel_order(order_id):
        api_broker.cancel_order_calls += 1
        return None

    monkeypatch.setattr(api_broker, "place_limit_order", place_limit_order)
    monkeypatch.setattr(api_broker, "cancel_order", cancel_order)

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_weekly_closes([110.0] * 35))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    assert api_broker.place_limit_order_calls == 0
    assert api_broker.cancel_order_calls == 0


@pytest.mark.asyncio
async def test_position_signals_approve_cancel_remain_forbidden(position_signals_client):
    approve = await position_signals_client.post("/api/v1/orders/approve", json={"order_id": "1"})
    cancel = await position_signals_client.post("/api/v1/orders/cancel", json={"order_id": "1"})
    assert approve.status_code == 403
    assert cancel.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "gain_pct,expected_signal",
    [
        (-5, "HOLD"),
        (-8, "REVIEW_POSITION"),
        (-15, "STOP_ADDING"),
        (-20, "REDUCE_RISK"),
        (-30, "EXIT_POSITION"),
    ],
)
async def test_position_signals_loss_side_guidance(position_signals_client, api_broker, api_kline_service, monkeypatch, gain_pct, expected_signal):
    await init_db()
    avg_cost = 100.0
    current_price = avg_cost * (1 + gain_pct / 100.0)
    position = PositionDto(
        symbol="META",
        quantity=100,
        avg_cost=avg_cost,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=10.0,
    )

    async def get_positions():
        return [position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)

    closes = [100.0] * 199 + [current_price]

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_daily_closes(closes))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    row = (await position_signals_client.get("/api/v1/position-signals")).json()[0]
    assert row["signal"] == expected_signal


@pytest.mark.asyncio
async def test_position_signals_price_below_sma200_reduces_risk(position_signals_client, api_broker, api_kline_service, monkeypatch):
    await init_db()
    position = PositionDto(
        symbol="AAPL",
        quantity=100,
        avg_cost=100.0,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=10.0,
    )

    async def get_positions():
        return [position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)

    closes = [105.0] * 199 + [80.0]

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_daily_closes(closes))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    row = (await position_signals_client.get("/api/v1/position-signals")).json()[0]
    assert row["signal"] == "REDUCE_RISK"


@pytest.mark.asyncio
async def test_position_signals_drawdown_exit(position_signals_client, api_broker, api_kline_service, monkeypatch):
    await init_db()
    position = PositionDto(
        symbol="NVDA",
        quantity=50,
        avg_cost=100.0,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=12.0,
    )

    async def get_positions():
        return [position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)

    closes = [100.0] * 180 + [160.0] * 19 + [100.0]

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_daily_closes(closes))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    from app.db.session import create_session_factory

    factory = create_session_factory()
    async with factory() as session:
        session.add(
            PositionLifecycleState(
                symbol="NVDA",
                original_entry_price=100.0,
                original_quantity=50,
                original_cost_basis=5000.0,
                highest_price_since_entry=160.0,
                trim_25_done=False,
                trim_50_done=False,
                trim_75_done=False,
                tail_mode=False,
                tail_started_at=None,
                tail_original_quantity=None,
                notes=None,
            )
        )
        await session.commit()

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    row = (await position_signals_client.get("/api/v1/position-signals")).json()[0]
    assert row["signal"] == "EXIT_POSITION"


@pytest.mark.asyncio
async def test_position_signals_no_orders_on_new_signals(position_signals_client, api_broker, api_kline_service, monkeypatch):
    await init_db()
    position = PositionDto(
        symbol="META",
        quantity=10,
        avg_cost=100.0,
        current_price=None,
        unrealized_pnl=None,
        day_pnl=None,
        stop_level=None,
        position_pct=2.0,
    )

    async def get_positions():
        return [position]

    async def get_quote(symbol):
        return QuoteDto(
            symbol=symbol,
            bid=None,
            ask=None,
            last=None,
            volume=None,
            bid_size=None,
            ask_size=None,
            timestamp=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(api_broker, "get_positions", get_positions)
    monkeypatch.setattr(api_broker, "get_quote", get_quote)
    api_broker.place_limit_order_calls = 0
    api_broker.cancel_order_calls = 0

    async def place_limit_order(request):
        api_broker.place_limit_order_calls += 1
        return None

    async def cancel_order(order_id):
        api_broker.cancel_order_calls += 1
        return None

    monkeypatch.setattr(api_broker, "place_limit_order", place_limit_order)
    monkeypatch.setattr(api_broker, "cancel_order", cancel_order)

    async def fetch(symbol, lookback_days=None, session=None):
        return _make_fetch_result(_bars_from_daily_closes([100.0] * 199 + [92.0]))

    monkeypatch.setattr(api_kline_service, "get_cached_or_fetch_daily_bars", fetch)

    resp = await position_signals_client.post("/api/v1/position-signals/run")
    assert resp.status_code == 200
    assert api_broker.place_limit_order_calls == 0
    assert api_broker.cancel_order_calls == 0
