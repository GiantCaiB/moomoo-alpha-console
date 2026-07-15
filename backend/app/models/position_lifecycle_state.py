from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class PositionLifecycleState(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "position_lifecycle_state"

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    original_entry_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    original_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    original_cost_basis: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    highest_price_since_entry: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trim_25_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trim_50_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trim_75_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tail_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tail_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tail_original_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
