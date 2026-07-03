from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin


class SignalScore(Base, UUIDMixin):
    __tablename__ = "signal_scores"

    signal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("signals.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[str | None] = mapped_column(nullable=True)
