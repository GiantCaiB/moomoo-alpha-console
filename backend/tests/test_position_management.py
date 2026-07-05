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


@pytest.mark.asyncio
async def test_position_signals_continues_after_cache_write_failure(api_broker, monkeypatch):
    """Cache write failure for one symbol does not crash the batch or poison lifecycle state.

    Tests:
    - Multi-symbol continuation across KLine cache write failure
    - No MissingGreenlet when accessing lifecycle state after K-line operations
    - One signal per active position
    """
    from app.services.kline.service import KLineService
    from app.services.position_management.profit_tail import ProfitTailStrategyService
    from app.services.market_data.price_resolver import PriceResolver
    from app.db.session import create_session_factory
    from sqlalchemy import delete as sa_delete
    from app.models.bar_1d import Bar1d

    await init_db()

    # Clear any cached bars that might interfere with this test
    factory = create_session_factory()
    async with factory() as s:
        await s.execute(sa_delete(Bar1d))
        await s.commit()

    fail_symbol_ksym = "FAILSYM"
    ok_symbol_ksym = "OKSYM"
    # Close prices corresponding to ~5% gain and ~75% gain (avg_cost=100)
    close_prices = {fail_symbol_ksym: 105.0, ok_symbol_ksym: 175.0}
    positions = [
        PositionDto(symbol="FAILSYM", quantity=100, avg_cost=100.0, current_price=None,
                    unrealized_pnl=None, day_pnl=None, stop_level=None, position_pct=5.0),
        PositionDto(symbol="OKSYM", quantity=100, avg_cost=100.0, current_price=None,
                    unrealized_pnl=None, day_pnl=None, stop_level=None, position_pct=5.0),
    ]

    class FakeProvider:
        def get_daily_bars(self, symbol, start_date, end_date, adjusted=True):
            base = close_prices.get(symbol, 102.0)
            dates = []
            current = start_date
            from datetime import timedelta
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
            closes = [(base + float(i) * 0.01) for i in range(400)]
            return pd.DataFrame({
                "date": dates[:400],
                "open": [c * 0.99 for c in closes],
                "high": [c * 1.01 for c in closes],
                "low": [c * 0.98 for c in closes],
                "close": closes,
                "volume": [1_000_000] * min(len(dates), 400),
                "adj_close": closes,
            })

    async def get_positions():
        return positions

    monkeypatch.setattr(api_broker, "get_positions", get_positions)

    async def null_quote(symbol):
        from app.services.broker.base import QuoteDto
        return QuoteDto(symbol=symbol, bid=None, ask=None, last=None, volume=None,
                        bid_size=None, ask_size=None, timestamp=datetime.now(timezone.utc))
    monkeypatch.setattr(api_broker, "get_quote", null_quote)

    provider = FakeProvider()
    kline = KLineService(provider=provider, enable_cache=True)

    original_write_cache = kline._write_cache

    async def failing_write_cache(symbol, df, session):
        if fail_symbol_ksym in symbol.upper():
            raise Exception(f"Simulated cache write failure for {symbol}")
        await original_write_cache(symbol, df, session)

    monkeypatch.setattr(kline, "_write_cache", failing_write_cache)

    resolver = PriceResolver(api_broker, kline)
    service = ProfitTailStrategyService(broker=api_broker, kline_service=kline, price_resolver=resolver)

    async with factory() as session:
        results, summary = await service.run(session)

        assert summary["status"] == "COMPLETED", f"Run failed: {summary}"
        assert summary["positions_scanned"] == 2
        assert summary["signals_generated"] == 2
        assert summary["data_error_count"] == 1

        symbols = {r.symbol for r in results}
        assert symbols == {"FAILSYM", "OKSYM"}, f"Expected FAILSYM and OKSYM, got {symbols}"

        meta = next(r for r in results if r.symbol == "FAILSYM")
        assert meta.signal == "DATA_ERROR", f"Expected DATA_ERROR for FAILSYM, got {meta.signal}"
        assert "Simulated cache write failure" in (meta.reason or "")

        ok = next(r for r in results if r.symbol == "OKSYM")
        assert ok.signal == "TRIM_PROFIT", f"Expected TRIM_PROFIT for OKSYM, got {ok.signal}"


@pytest.mark.asyncio
async def test_one_latest_signal_per_position(api_broker, monkeypatch):
    """Run produces exactly one latest signal per active position (no duplicates)."""
    from app.services.kline.service import KLineService
    from app.services.position_management.profit_tail import ProfitTailStrategyService
    from app.services.market_data.price_resolver import PriceResolver
    from app.db.session import create_session_factory
    from sqlalchemy import delete as sa_delete
    from app.models.bar_1d import Bar1d

    await init_db()

    factory = create_session_factory()
    async with factory() as s:
        await s.execute(sa_delete(Bar1d))
        await s.commit()

    syms = ["SYMA", "SYMB", "SYMC"]
    positions = [
        PositionDto(symbol=s, quantity=100, avg_cost=100.0, current_price=None,
                    unrealized_pnl=None, day_pnl=None, stop_level=None, position_pct=5.0)
        for s in syms
    ]

    class FakeProvider:
        def get_daily_bars(self, symbol, start_date, end_date, adjusted=True):
            close = 102.0
            dates = []
            current = start_date
            from datetime import timedelta
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
            closes = [(close + float(i) * 0.01) for i in range(400)]
            return pd.DataFrame({
                "date": dates[:400],
                "open": [c * 0.99 for c in closes],
                "high": [c * 1.01 for c in closes],
                "low": [c * 0.98 for c in closes],
                "close": closes,
                "volume": [1_000_000] * min(len(dates), 400),
                "adj_close": closes,
            })

    async def get_positions():
        return positions

    monkeypatch.setattr(api_broker, "get_positions", get_positions)

    async def null_quote(symbol):
        from app.services.broker.base import QuoteDto
        return QuoteDto(symbol=symbol, bid=None, ask=None, last=None, volume=None,
                        bid_size=None, ask_size=None, timestamp=datetime.now(timezone.utc))
    monkeypatch.setattr(api_broker, "get_quote", null_quote)

    kline = KLineService(provider=FakeProvider(), enable_cache=True)
    resolver = PriceResolver(api_broker, kline)
    service = ProfitTailStrategyService(broker=api_broker, kline_service=kline, price_resolver=resolver)

    async with factory() as session:
        results, summary = await service.run(session)

        assert summary["status"] == "COMPLETED"
        assert summary["signals_generated"] == 3

        symbols = [r.symbol for r in results]
        assert len(symbols) == len(set(symbols)), f"Duplicate symbols in results: {symbols}"
        assert set(symbols) == set(syms)


@pytest.mark.asyncio
async def test_no_missing_greenlet_on_cache_write_failure(api_broker, monkeypatch):
    """No MissingGreenlet when accessing lifecycle state after KLine cache write failure.

    Tests that ProfitTailEvalState prevents lazy-load on expired ORM state.
    """
    from app.services.kline.service import KLineService
    from app.services.position_management.profit_tail import ProfitTailStrategyService
    from app.services.market_data.price_resolver import PriceResolver
    from app.db.session import create_session_factory
    from sqlalchemy import delete as sa_delete
    from app.models.bar_1d import Bar1d

    await init_db()

    factory = create_session_factory()
    async with factory() as s:
        await s.execute(sa_delete(Bar1d))
        await s.commit()

    position = PositionDto(symbol="ZXCV", quantity=100, avg_cost=100.0, current_price=None,
                           unrealized_pnl=None, day_pnl=None, stop_level=None, position_pct=5.0)

    class FakeProvider:
        def get_daily_bars(self, symbol, start_date, end_date, adjusted=True):
            close = 102.0
            dates = []
            current = start_date
            from datetime import timedelta
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
            closes = [(close + float(i) * 0.01) for i in range(400)]
            return pd.DataFrame({
                "date": dates[:400],
                "open": [c * 0.99 for c in closes],
                "high": [c * 1.01 for c in closes],
                "low": [c * 0.98 for c in closes],
                "close": closes,
                "volume": [1_000_000] * min(len(dates), 400),
                "adj_close": closes,
            })

    async def get_positions():
        return [position]

    monkeypatch.setattr(api_broker, "get_positions", get_positions)

    async def null_quote(symbol):
        from app.services.broker.base import QuoteDto
        return QuoteDto(symbol=symbol, bid=None, ask=None, last=None, volume=None,
                        bid_size=None, ask_size=None, timestamp=datetime.now(timezone.utc))
    monkeypatch.setattr(api_broker, "get_quote", null_quote)

    kline = KLineService(provider=FakeProvider(), enable_cache=True)

    async def fail_every_write(symbol, df, session):
        raise Exception("Simulated cache write failure")

    monkeypatch.setattr(kline, "_write_cache", fail_every_write)

    resolver = PriceResolver(api_broker, kline)
    service = ProfitTailStrategyService(broker=api_broker, kline_service=kline, price_resolver=resolver)

    async with factory() as session:
        # This must not raise MissingGreenlet error.
        # ProfitTailEvalState prevents lazy-load on expired ORM state.
        results, summary = await service.run(session)

        assert summary["status"] == "COMPLETED"
        assert summary["signals_generated"] == 1
        assert summary["data_error_count"] == 1

        result = results[0]
        assert result.symbol == "ZXCV"
        assert result.signal == "DATA_ERROR"
        assert "Simulated cache write failure" in (result.reason or "")


async def _insert_signal(session, symbol: str, signal: str = "HOLD", **kw):
    """Helper to insert a position management signal row."""
    from app.models.position_management_signal import PositionManagementSignal
    session.add(PositionManagementSignal(
        symbol=symbol,
        signal=signal,
        reason=kw.get("reason", ""),
        current_price=kw.get("current_price", 150.0),
        avg_cost=kw.get("avg_cost", 100.0),
        quantity=kw.get("quantity", 100),
        gain_pct=kw.get("gain_pct", 50.0),
        suggested_action=kw.get("suggested_action", "Hold"),
        tail_mode=kw.get("tail_mode", False),
        data_source="moomoo_positions_plus_yfinance_kline",
        price_source="test",
        bar_source="test",
        is_real_market_data=True,
        generated_at=datetime.now(timezone.utc),
    ))


@pytest.mark.asyncio
async def test_list_signals_filters_by_default_with_active_symbols(api_broker, monkeypatch):
    """list_signals with active_symbols excludes stale/test symbols."""
    from app.services.kline.service import KLineService
    from app.services.position_management.profit_tail import ProfitTailStrategyService
    from app.services.market_data.price_resolver import PriceResolver
    from app.db.session import create_session_factory

    await init_db()
    kline = KLineService(provider=None, enable_cache=False)
    resolver = PriceResolver(api_broker, kline)
    service = ProfitTailStrategyService(broker=api_broker, kline_service=kline, price_resolver=resolver)

    factory = create_session_factory()
    async with factory() as session:
        await _insert_signal(session, "ZXCV")
        await _insert_signal(session, "AAPL")
        await _insert_signal(session, "MSFT")
        await session.commit()

    active_symbols = {"AAPL", "MSFT"}

    async with factory() as session:
        results = await service.list_signals(session, include_history=False, active_symbols=active_symbols)

    symbols = {r.symbol for r in results}
    assert "ZXCV" not in symbols, "Stale symbol ZXCV should be excluded"
    assert symbols == {"AAPL", "MSFT"}


@pytest.mark.asyncio
async def test_list_signals_include_history_still_filters_by_active_symbols(api_broker, monkeypatch):
    """include_history=true still respects active_symbols filter by default."""
    from app.services.kline.service import KLineService
    from app.services.position_management.profit_tail import ProfitTailStrategyService
    from app.services.market_data.price_resolver import PriceResolver
    from app.db.session import create_session_factory

    await init_db()
    kline = KLineService(provider=None, enable_cache=False)
    resolver = PriceResolver(api_broker, kline)
    service = ProfitTailStrategyService(broker=api_broker, kline_service=kline, price_resolver=resolver)

    factory = create_session_factory()
    async with factory() as session:
        await _insert_signal(session, "ZXCV")
        await _insert_signal(session, "AAPL", generated_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
        await _insert_signal(session, "AAPL", generated_at=datetime(2025, 6, 1, tzinfo=timezone.utc))
        await _insert_signal(session, "MSFT")
        await session.commit()

    active_symbols = {"AAPL", "MSFT"}

    async with factory() as session:
        results = await service.list_signals(session, include_history=True, active_symbols=active_symbols)

    symbols = {r.symbol for r in results}
    assert "ZXCV" not in symbols, "Stale symbol ZXCV should be excluded even with include_history"
    assert "AAPL" in symbols
    assert "MSFT" in symbols
    assert len(results) >= 2, "Include_history should return multiple rows per symbol"


@pytest.mark.asyncio
async def test_get_position_signals_api_excludes_stale_by_default(position_signals_client, api_broker, monkeypatch):
    """GET /api/v1/position-signals excludes stale symbols by default."""
    from app.db.session import create_session_factory

    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        await _insert_signal(session, "ZXCV")
        await _insert_signal(session, "AAPL")
        await _insert_signal(session, "MSFT")
        await session.commit()

    # Mock broker to return only AAPL, MSFT as active positions
    async def get_active_positions():
        return [
            PositionDto(symbol="AAPL", quantity=100, avg_cost=100.0, current_price=150.0,
                        unrealized_pnl=5000.0, day_pnl=100.0, stop_level=None, position_pct=10.0),
            PositionDto(symbol="MSFT", quantity=50, avg_cost=200.0, current_price=220.0,
                        unrealized_pnl=1000.0, day_pnl=50.0, stop_level=None, position_pct=5.0),
        ]
    monkeypatch.setattr(api_broker, "get_positions", get_active_positions)

    response = await position_signals_client.get("/api/v1/position-signals")
    assert response.status_code == 200
    data = response.json()
    symbols = [row["symbol"] for row in data]
    assert "ZXCV" not in symbols, f"Stale symbol ZXCV should not appear in response: {symbols}"
    assert "AAPL" in symbols
    assert "MSFT" in symbols


@pytest.mark.asyncio
async def test_get_position_signals_api_include_inactive_returns_all(position_signals_client, api_broker, monkeypatch):
    """GET /api/v1/position-signals?include_inactive=true returns stale symbols too."""
    from app.db.session import create_session_factory

    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        await _insert_signal(session, "ZXCV")
        await _insert_signal(session, "AAPL")
        await _insert_signal(session, "MSFT")
        await session.commit()

    async def get_active_positions():
        return [
            PositionDto(symbol="AAPL", quantity=100, avg_cost=100.0, current_price=150.0,
                        unrealized_pnl=5000.0, day_pnl=100.0, stop_level=None, position_pct=10.0),
        ]
    monkeypatch.setattr(api_broker, "get_positions", get_active_positions)

    response = await position_signals_client.get("/api/v1/position-signals?include_inactive=true")
    assert response.status_code == 200
    data = response.json()
    symbols = {row["symbol"] for row in data}
    assert "ZXCV" in symbols, "ZXCV should appear when include_inactive=true"
    assert "AAPL" in symbols
    assert "MSFT" in symbols


@pytest.mark.asyncio
async def test_get_position_signals_api_returns_empty_when_broker_fails(position_signals_client, api_broker, monkeypatch):
    """GET /api/v1/position-signals returns empty list when broker positions fail to load."""
    from app.db.session import create_session_factory

    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        await _insert_signal(session, "ZXCV")
        await _insert_signal(session, "AAPL")
        await session.commit()

    async def failing_get_positions():
        raise Exception("Broker connection lost")

    monkeypatch.setattr(api_broker, "get_positions", failing_get_positions)

    response = await position_signals_client.get("/api/v1/position-signals")
    assert response.status_code == 200
    data = response.json()
    assert data == [], "Should return empty list when broker positions cannot be loaded"


@pytest.mark.asyncio
async def test_delete_stale_position_signals(position_signals_client, api_broker, monkeypatch):
    """DELETE /api/v1/position-signals/stale removes symbols not in current active positions."""
    from app.db.session import create_session_factory

    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        await _insert_signal(session, "ZXCV")
        await _insert_signal(session, "AAPL")
        await _insert_signal(session, "MSFT")
        await session.commit()

    async def get_active_positions():
        return [
            PositionDto(symbol="AAPL", quantity=100, avg_cost=100.0, current_price=150.0,
                        unrealized_pnl=5000.0, day_pnl=100.0, stop_level=None, position_pct=10.0),
            PositionDto(symbol="MSFT", quantity=50, avg_cost=200.0, current_price=220.0,
                        unrealized_pnl=1000.0, day_pnl=50.0, stop_level=None, position_pct=5.0),
        ]
    monkeypatch.setattr(api_broker, "get_positions", get_active_positions)

    response = await position_signals_client.delete("/api/v1/position-signals/stale")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted_count"] == 1
    assert "ZXCV" in data["deleted_symbols"]
    assert "AAPL" in data["active_symbols"]
    assert "MSFT" in data["active_symbols"]

    # Verify ZXCV is really gone from DB
    async with factory() as session:
        from sqlalchemy import select
        from app.models.position_management_signal import PositionManagementSignal
        result = await session.execute(select(PositionManagementSignal.symbol).where(PositionManagementSignal.symbol == "ZXCV"))
        remaining = result.scalars().all()
        assert len(remaining) == 0, "ZXCV should have been deleted"


@pytest.mark.asyncio
async def test_delete_stale_position_signals_dry_run(position_signals_client, api_broker, monkeypatch):
    """DELETE /api/v1/position-signals/stale?dry_run=true does not actually delete."""
    from app.db.session import create_session_factory

    await init_db()
    factory = create_session_factory()
    async with factory() as session:
        await _insert_signal(session, "ZXCV")
        await _insert_signal(session, "AAPL")
        await session.commit()

    async def get_active_positions():
        return [
            PositionDto(symbol="AAPL", quantity=100, avg_cost=100.0, current_price=150.0,
                        unrealized_pnl=5000.0, day_pnl=100.0, stop_level=None, position_pct=10.0),
        ]
    monkeypatch.setattr(api_broker, "get_positions", get_active_positions)

    response = await position_signals_client.delete("/api/v1/position-signals/stale?dry_run=true")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted_count"] == 1
    assert "ZXCV" in data["deleted_symbols"]

    # Verify ZXCV still exists in DB (dry run)
    async with factory() as session:
        from sqlalchemy import select
        from app.models.position_management_signal import PositionManagementSignal
        result = await session.execute(select(PositionManagementSignal.symbol).where(PositionManagementSignal.symbol == "ZXCV"))
        remaining = result.scalars().all()
        assert len(remaining) == 1, "ZXCV should still exist after dry run"
