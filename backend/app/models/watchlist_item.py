from sqlalchemy import String, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class WatchlistItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "watchlist_items"

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    list_name: Mapped[str] = mapped_column(String(50), default="default")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    added_price: Mapped[float | None] = mapped_column(Float, nullable=True)
