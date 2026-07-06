from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Signal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "signals"

    strategy_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("strategy_runs.id"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_size_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    invalidation: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved: Mapped[bool | None] = mapped_column(default=None)
    signal_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    strategy_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    universe_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    price_as_of: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bar_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_real_market_data: Mapped[bool] = mapped_column(Boolean, default=False)
    is_tradeable: Mapped[bool] = mapped_column(Boolean, default=False)
    has_error: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_filters: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_quality_status: Mapped[str] = mapped_column(String(30), default="OK")
    calculated_score_before_filters: Mapped[float | None] = mapped_column(Float, nullable=True)

    strategy_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("strategy_profiles.id"), nullable=True
    )
    strategy_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parameters_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
