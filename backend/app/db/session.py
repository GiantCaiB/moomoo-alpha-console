import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite+aiosqlite:///./"):
        rel = url.removeprefix("sqlite+aiosqlite:///./")
        abs_path = Path.cwd() / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{abs_path.as_posix()}"
    return url


def create_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        db_url = get_db_path()
        _engine = create_async_engine(
            db_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        )
    return _engine


def create_session_factory(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        eng = engine or create_engine()
        _session_factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncSession:
    factory = create_session_factory()
    async with factory() as session:
        yield session


async def close_engine() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def init_db() -> None:
    from app.db.base import Base
    from app.models import (  # noqa: F401
        AppSetting,
        AuditLog,
        Bar1d,
        Fill,
        Order,
        PortfolioSnapshot,
        Position,
        RiskEvent,
        Signal,
        SignalScore,
        StrategyRun,
        Symbol,
        TradeJournalEntry,
        WatchlistItem,
    )
    engine = create_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
