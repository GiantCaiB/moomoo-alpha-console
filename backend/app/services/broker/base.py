from dataclasses import dataclass
from typing import Protocol
from datetime import datetime


@dataclass
class AccountSummary:
    total_value: float
    cash: float
    positions_value: float
    day_pnl: float
    day_pnl_pct: float
    total_pnl: float
    total_pnl_pct: float
    drawdown_pct: float
    buying_power: float
    currency: str = "USD"


@dataclass
class PositionDto:
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float | None
    unrealized_pnl: float | None
    day_pnl: float | None
    stop_level: float | None
    position_pct: float | None
    status: str = "OPEN"


@dataclass
class OrderDto:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    filled_quantity: int
    limit_price: float | None
    stop_price: float | None
    status: str
    reason: str | None
    created_at: datetime | None
    submitted_at: datetime | None
    filled_at: datetime | None
    cancelled_at: datetime | None


@dataclass
class QuoteDto:
    symbol: str
    bid: float | None
    ask: float | None
    last: float | None
    volume: float | None
    bid_size: int | None
    ask_size: int | None
    timestamp: datetime


@dataclass
class LimitOrderRequest:
    symbol: str
    side: str
    quantity: int
    limit_price: float
    stop_level: float | None = None
    reason: str | None = None


@dataclass
class BrokerHealth:
    connected: bool
    latency_ms: float | None
    message: str | None


class BrokerAdapter(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def health_check(self) -> BrokerHealth: ...
    async def get_account(self) -> AccountSummary: ...
    async def get_positions(self) -> list[PositionDto]: ...
    async def get_open_orders(self) -> list[OrderDto]: ...
    async def get_quote(self, symbol: str) -> QuoteDto: ...
    async def place_limit_order(self, request: LimitOrderRequest) -> OrderDto: ...
    async def cancel_order(self, order_id: str) -> None: ...
