import uuid
import random
from datetime import datetime, timezone, timedelta

from app.services.broker.base import (
    BrokerAdapter,
    AccountSummary,
    PositionDto,
    OrderDto,
    QuoteDto,
    LimitOrderRequest,
    BrokerHealth,
)


MOCK_POSITIONS_DATA: dict[str, dict] = {
    "AAPL": {"qty": 10, "cost": 198.50, "stop": 185.00},
    "MSFT": {"qty": 5, "cost": 420.00, "stop": 395.00},
    "NVDA": {"qty": 8, "cost": 880.00, "stop": 820.00},
}

BASE_PRICES: dict[str, float] = {
    "SPY": 540.0, "QQQ": 475.0, "AAPL": 210.0, "MSFT": 430.0,
    "NVDA": 920.0, "AMZN": 195.0, "META": 540.0, "GOOGL": 180.0,
    "TSLA": 250.0, "AMD": 160.0, "AVGO": 1750.0, "COST": 870.0, "NFLX": 700.0,
}


def _jitter(base: float, pct: float = 0.02) -> float:
    return round(base * (1 + random.uniform(-pct, pct)), 2)


class MockBrokerAdapter:
    def __init__(self) -> None:
        self._connected = False
        self._orders: list[OrderDto] = []
        self._open_orders: list[OrderDto] = []

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def health_check(self) -> BrokerHealth:
        return BrokerHealth(
            connected=self._connected,
            latency_ms=random.uniform(1.0, 15.0),
            message="Mock broker OK" if self._connected else "Mock broker disconnected",
        )

    async def get_account(self) -> AccountSummary:
        pos_value = 0.0
        for sym, p in MOCK_POSITIONS_DATA.items():
            price = _jitter(BASE_PRICES.get(sym, 100.0))
            pos_value += p["qty"] * price

        cash = 50000.0
        total = cash + pos_value
        cost_basis = sum(p["qty"] * p["cost"] for p in MOCK_POSITIONS_DATA.values())
        total_pnl = pos_value - cost_basis
        day_pnl = total_pnl * random.uniform(-0.02, 0.03)

        return AccountSummary(
            total_value=round(total, 2),
            cash=cash,
            positions_value=round(pos_value, 2),
            day_pnl=round(day_pnl, 2),
            day_pnl_pct=round(day_pnl / total * 100, 2) if total else 0.0,
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl / (total - total_pnl) * 100, 2) if (total - total_pnl) else 0.0,
            drawdown_pct=round(random.uniform(0.0, 3.0), 2),
            buying_power=cash * 2,
        )

    async def get_positions(self) -> list[PositionDto]:
        result: list[PositionDto] = []
        for sym, p in MOCK_POSITIONS_DATA.items():
            price = _jitter(BASE_PRICES.get(sym, 100.0))
            upnl = (price - p["cost"]) * p["qty"]
            pos_value = price * p["qty"]
            total_value = 50000.0 + sum(
                _jitter(BASE_PRICES.get(s, 100.0)) * pd["qty"]
                for s, pd in MOCK_POSITIONS_DATA.items()
            )
            pct = round(pos_value / total_value * 100, 2) if total_value else 0.0
            result.append(PositionDto(
                symbol=sym,
                quantity=p["qty"],
                avg_cost=p["cost"],
                current_price=price,
                unrealized_pnl=round(upnl, 2),
                day_pnl=round(upnl * random.uniform(-0.03, 0.03), 2),
                stop_level=p["stop"],
                position_pct=pct,
            ))
        return result

    async def get_open_orders(self) -> list[OrderDto]:
        return [
            o for o in self._open_orders
            if o.status in ("PENDING", "SUBMITTED")
        ]

    async def get_quote(self, symbol: str) -> QuoteDto:
        base = BASE_PRICES.get(symbol, 100.0)
        last = _jitter(base)
        spread = round(last * 0.001, 2)
        return QuoteDto(
            symbol=symbol,
            bid=round(last - spread, 2),
            ask=round(last + spread, 2),
            last=last,
            volume=random.randint(100000, 5000000),
            bid_size=random.randint(100, 1000),
            ask_size=random.randint(100, 1000),
            timestamp=datetime.now(timezone.utc),
        )

    async def place_limit_order(self, request: LimitOrderRequest) -> OrderDto:
        now = datetime.now(timezone.utc)
        order = OrderDto(
            order_id=str(uuid.uuid4()),
            symbol=request.symbol,
            side=request.side,
            order_type="LIMIT",
            quantity=request.quantity,
            filled_quantity=0,
            limit_price=request.limit_price,
            stop_price=request.stop_level,
            status="SUBMITTED",
            reason=request.reason,
            created_at=now,
            submitted_at=now,
            filled_at=None,
            cancelled_at=None,
        )
        self._open_orders.append(order)
        self._orders.append(order)
        return order

    async def cancel_order(self, order_id: str) -> None:
        for o in self._open_orders:
            if o.order_id == order_id:
                o.status = "CANCELLED"
                o.cancelled_at = datetime.now(timezone.utc)
                break
