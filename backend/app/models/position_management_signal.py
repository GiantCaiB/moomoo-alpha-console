from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class PositionManagementSignal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "position_management_signals"

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    signal: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    gain_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_trim_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    tail_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weekly_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_sma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_sma30: Mapped[float | None] = mapped_column(Float, nullable=True)
    drawdown_from_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_cost_basis: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_price_since_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    price_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bar_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_real_market_data: Mapped[bool] = mapped_column(Boolean, default=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    strategy_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("strategy_profiles.id"), nullable=True
    )
    strategy_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parameters_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
