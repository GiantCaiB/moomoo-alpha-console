from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class StrategyRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "strategy_runs"

    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    symbols_screened: Mapped[int] = mapped_column(default=0)
    signals_generated: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_error_count: Mapped[int] = mapped_column(Integer, default=0)
    data_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    universe_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
