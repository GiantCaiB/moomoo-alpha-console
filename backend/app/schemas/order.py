from datetime import datetime
from pydantic import BaseModel


class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    filled_quantity: int
    limit_price: float | None
    stop_price: float | None
    status: str
    reason: str | None
    risk_check_passed: bool | None
    risk_details: str | None
    signal_id: str | None
    created_at: datetime
    submitted_at: datetime | None
    filled_at: datetime | None
    cancelled_at: datetime | None
    notes: str | None


class LimitOrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: int
    limit_price: float
    stop_level: float | None = None
    signal_id: str | None = None
    reason: str | None = None


class PreviewOrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: int
    limit_price: float
    stop_level: float | None = None


class PreviewOrderResponse(BaseModel):
    allowed: bool
    reasons: list[str]
    warnings: list[str]
    max_allowed_quantity: int | None


class ApproveOrderRequest(BaseModel):
    order_id: str


class CancelOrderRequest(BaseModel):
    order_id: str
