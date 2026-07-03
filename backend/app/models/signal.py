from datetime import datetime
from sqlalchemy import String, Float, DateTime, Text, ForeignKey
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
