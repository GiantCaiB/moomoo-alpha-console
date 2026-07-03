import uuid
import random
from datetime import datetime, timezone

from app.services.broker.base import (
    BrokerAdapter,
    AccountSummary,
    PositionDto,
    OrderDto,
    QuoteDto,
    LimitOrderRequest,
    BrokerHealth,
)
from app.services.broker.mock import MockBrokerAdapter, BASE_PRICES, _jitter, MOCK_POSITIONS_DATA


class PaperBrokerAdapter:
    def __init__(self) -> None:
        self._mock = MockBrokerAdapter()
        self._filled_orders: list[OrderDto] = []
        self._open_orders: list[OrderDto] = []
        self._cash = 100000.0
        self._positions: dict[str, dict] = {}
        self._trade_log: list[dict] = []

    async def connect(self) -> None:
        await self._mock.connect()

    async def disconnect(self) -> None:
        await self._mock.disconnect()

    async def health_check(self) -> BrokerHealth:
        return await self._mock.health_check()

    async def get_account(self) -> AccountSummary:
        pos_value = 0.0
        for sym, pdata in self._positions.items():
            price = _jitter(BASE_PRICES.get(sym, 100.0))
            pos_value += pdata["qty"] * price

        cash = self._cash
        total = cash + pos_value
        total_pnl = sum(
            (_jitter(BASE_PRICES.get(s, 100.0)) - p["cost"]) * p["qty"]
            for s, p in self._positions.items()
        ) if self._positions else 0.0

        return AccountSummary(
            total_value=round(total, 2),
            cash=cash,
            positions_value=round(pos_value, 2),
            day_pnl=round(total_pnl * random.uniform(-0.02, 0.03), 2),
            day_pnl_pct=0.0,
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=0.0,
            drawdown_pct=0.0,
            buying_power=cash * 2,
        )

    async def get_positions(self) -> list[PositionDto]:
        result: list[PositionDto] = []
        for sym, pdata in self._positions.items():
            price = _jitter(BASE_PRICES.get(sym, 100.0))
            upnl = (price - pdata["cost"]) * pdata["qty"]
            pos_value = price * pdata["qty"]
            total_value = self._cash + sum(
                _jitter(BASE_PRICES.get(s, 100.0)) * pd["qty"]
                for s, pd in self._positions.items()
            )
            pct = round(pos_value / total_value * 100, 2) if total_value else 0.0
            result.append(PositionDto(
                symbol=sym,
                quantity=pdata["qty"],
                avg_cost=pdata["cost"],
                current_price=price,
                unrealized_pnl=round(upnl, 2),
                day_pnl=0.0,
                stop_level=pdata.get("stop"),
                position_pct=pct,
            ))
        return result

    async def get_open_orders(self) -> list[OrderDto]:
        return [o for o in self._open_orders if o.status in ("PENDING", "SUBMITTED")]

    async def get_quote(self, symbol: str) -> QuoteDto:
        return await self._mock.get_quote(symbol)

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
        self._trade_log.append({
            "action": "PLACE_LIMIT",
            "order_id": order.order_id,
            "symbol": request.symbol,
            "side": request.side,
            "qty": request.quantity,
            "price": request.limit_price,
            "time": now.isoformat(),
        })
        return order

    async def cancel_order(self, order_id: str) -> None:
        for o in self._open_orders:
            if o.order_id == order_id:
                o.status = "CANCELLED"
                o.cancelled_at = datetime.now(timezone.utc)
                self._trade_log.append({
                    "action": "CANCEL",
                    "order_id": order_id,
                    "time": datetime.now(timezone.utc).isoformat(),
                })
                break

    def get_trade_log(self) -> list[dict]:
        return self._trade_log
