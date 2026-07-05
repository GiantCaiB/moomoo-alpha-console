import logging
import inspect
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.kline.base import KLineProvider
from app.services.kline.symbol_map import normalize_symbol, to_kline_symbol
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KLineFetchResult:
    symbol: str
    bars: pd.DataFrame
    cached_bars_available: bool
    cached_bar_count: int
    latest_cached_close: float | None
    latest_cached_bar_date: str | None
    fetch_attempted: bool
    fetch_failed: bool
    fetch_error: str | None
    latest_bar_from_current_fetch: str | None
    source: str
    last_error: str | None = None


class KLineService:
    def __init__(self, provider: KLineProvider, enable_cache: bool = True) -> None:
        self._provider = provider
        self._enable_cache = enable_cache
        self.requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.upstream_fetches = 0
        self.failed = 0
        self.latest_successful_fetch: datetime | None = None
        self._per_symbol: dict[str, dict] = {}
        self._bars_table_columns: set[str] | None = None
        self._last_fetch_error: str | None = None

    async def _bars_1d_columns(self, session: AsyncSession) -> set[str]:
        if self._bars_table_columns is not None:
            return self._bars_table_columns

        def _load_columns(sync_session) -> set[str]:
            result = sync_session.execute(text("PRAGMA table_info(bars_1d)"))
            return {str(row[1]) for row in result.fetchall()}

        try:
            self._bars_table_columns = await session.run_sync(_load_columns)
        except Exception as e:
            logger.warning("Unable to inspect bars_1d schema: %s", e)
            self._bars_table_columns = set()
        return self._bars_table_columns

    async def get_daily_bars(
        self,
        symbol: str,
        lookback_days: int | None = None,
        session: AsyncSession | None = None,
    ) -> pd.DataFrame:
        result = await self.get_cached_or_fetch_daily_bars(symbol, lookback_days=lookback_days, session=session)
        return result.bars

    async def get_cached_or_fetch_daily_bars(
        self,
        symbol: str,
        lookback_days: int | None = None,
        session: AsyncSession | None = None,
    ) -> KLineFetchResult:
        normalized = normalize_symbol(symbol)
        if normalized is None:
            logger.warning("Rejecting invalid symbol for K-line fetch: %r (source=screening_universe)", symbol)
            empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"])
            return KLineFetchResult(
                symbol=symbol,
                bars=empty,
                cached_bars_available=False,
                cached_bar_count=0,
                latest_cached_close=None,
                latest_cached_bar_date=None,
                fetch_attempted=False,
                fetch_failed=False,
                fetch_error="invalid_symbol",
                latest_bar_from_current_fetch=None,
                source="invalid_symbol",
                last_error="invalid_symbol",
            )

        info = to_kline_symbol(normalized)
        ksym = info.kline_symbol
        if not ksym:
            logger.warning("Rejecting invalid symbol for K-line fetch: %r (source=screening_universe)", symbol)
            empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"])
            return KLineFetchResult(
                symbol=normalized,
                bars=empty,
                cached_bars_available=False,
                cached_bar_count=0,
                latest_cached_close=None,
                latest_cached_bar_date=None,
                fetch_attempted=False,
                fetch_failed=False,
                fetch_error="invalid_symbol",
                latest_bar_from_current_fetch=None,
                source="invalid_symbol",
                last_error="invalid_symbol",
            )
        lb = lookback_days or settings.kline_lookback_days
        end = date.today()
        start = end - timedelta(days=lb)

        self.requests += 1
        previous_failed = self.failed
        self._last_fetch_error = None

        if self._enable_cache and session is not None:
            cached = await self._load_cached(ksym, start, end, session)
            if cached is not None and len(cached) > 0:
                latest_bar = cached["bar_date"].max()
                latest_bar = self._coerce_date(latest_bar)
                if latest_bar is not None and latest_bar >= end - timedelta(days=5):
                    self.cache_hits += 1
                    self._track(ksym, len(cached), "cache", None)
                    latest_close = None
                    latest_bar_date = None
                    if "close" in cached.columns and not cached.empty:
                        latest_close = float(cached["close"].iloc[-1])
                    if "bar_date" in cached.columns and not cached.empty:
                        bar_date = cached["bar_date"].iloc[-1]
                        latest_bar_date = bar_date.isoformat() if hasattr(bar_date, "isoformat") else str(bar_date)
                    return KLineFetchResult(
                        symbol=normalized,
                        bars=cached,
                        cached_bars_available=True,
                        cached_bar_count=len(cached),
                        latest_cached_close=latest_close,
                        latest_cached_bar_date=latest_bar_date,
                        fetch_attempted=False,
                        fetch_failed=False,
                        fetch_error=None,
                        latest_bar_from_current_fetch=None,
                        source="cache",
                        last_error=None,
                    )

        self.cache_misses += 1
        df = await self._fetch(ksym, start, end)

        if df.empty:
            last_error = self._last_fetch_error or ("fetch_failed" if self.failed > previous_failed else "empty_result")
            self._track(ksym, 0, "upstream", last_error)
            return KLineFetchResult(
                symbol=normalized,
                bars=df,
                cached_bars_available=False,
                cached_bar_count=0,
                latest_cached_close=None,
                latest_cached_bar_date=None,
                fetch_attempted=True,
                fetch_failed=True,
                fetch_error=last_error,
                latest_bar_from_current_fetch=None,
                source="upstream",
                last_error=last_error,
            )

        if self._enable_cache and session is not None:
            await self._write_cache(ksym, df, session)

        self._track(ksym, len(df), "upstream", None)
        latest_bar = df["date"].iloc[-1] if "date" in df.columns and not df.empty else None
        latest_bar_date = latest_bar.isoformat() if hasattr(latest_bar, "isoformat") else (str(latest_bar) if latest_bar is not None else None)
        latest_close = float(df["adj_close"].iloc[-1]) if "adj_close" in df.columns and not df.empty else (
            float(df["close"].iloc[-1]) if "close" in df.columns and not df.empty else None
        )
        return KLineFetchResult(
            symbol=normalized,
            bars=df,
            cached_bars_available=False,
            cached_bar_count=len(df),
            latest_cached_close=latest_close,
            latest_cached_bar_date=latest_bar_date,
            fetch_attempted=True,
            fetch_failed=False,
            fetch_error=None,
            latest_bar_from_current_fetch=latest_bar_date,
            source="upstream",
            last_error=None,
        )

    async def get_latest_cached_close(self, symbol: str, session: AsyncSession | None = None) -> float | None:
        normalized = normalize_symbol(symbol)
        if normalized is None or session is None or not self._enable_cache:
            return None
        info = to_kline_symbol(normalized)
        ksym = info.kline_symbol
        if not ksym:
            return None
        try:
            columns = await self._bars_1d_columns(session)
            if not columns or "close" not in columns or "bar_date" not in columns:
                return None
            stmt = text(
                "SELECT bar_date, close "
                "FROM bars_1d "
                "WHERE symbol = :symbol "
                "ORDER BY bar_date DESC "
                "LIMIT 1"
            )
            result = await session.execute(stmt, {"symbol": ksym})
            row = result.mappings().first()
            if row is None:
                return None
            return float(row["close"])
        except Exception as e:
            logger.warning("Latest cached close lookup failed for %s: %s", ksym, e)
            return None

    async def has_cached_bars(self, symbol: str, session: AsyncSession | None = None, minimum: int = 1) -> bool:
        status = await self.get_symbol_status(symbol, session=session)
        return bool(status["cached_bars_available"]) and int(status["cached_bar_count"]) >= minimum

    async def get_symbol_status(self, symbol: str, session: AsyncSession | None = None) -> dict:
        normalized = normalize_symbol(symbol)
        if normalized is None or session is None or not self._enable_cache:
            return {
                "symbol": symbol,
                "kline_symbol": None,
                "symbol_mapping_ok": False,
                "cached_bars_available": False,
                "cached_bar_count": 0,
                "latest_cached_close": None,
                "latest_cached_bar_date": None,
                "has_minimum_bars": False,
            }

        info = to_kline_symbol(normalized)
        ksym = info.kline_symbol
        if not ksym:
            return {
                "symbol": normalized,
                "kline_symbol": None,
                "symbol_mapping_ok": False,
                "cached_bars_available": False,
                "cached_bar_count": 0,
                "latest_cached_close": None,
                "latest_cached_bar_date": None,
                "has_minimum_bars": False,
            }

        try:
            columns = await self._bars_1d_columns(session)
            if not columns or "bar_date" not in columns or "close" not in columns:
                return {
                    "symbol": normalized,
                    "kline_symbol": ksym,
                    "symbol_mapping_ok": True,
                    "cached_bars_available": False,
                    "cached_bar_count": 0,
                    "latest_cached_close": None,
                    "latest_cached_bar_date": None,
                    "has_minimum_bars": False,
                }

            count_stmt = text(
                "SELECT COUNT(*) AS bar_count "
                "FROM bars_1d "
                "WHERE symbol = :symbol"
            )
            count_result = await session.execute(count_stmt, {"symbol": ksym})
            cached_bar_count = int(count_result.mappings().first()["bar_count"] or 0)

            latest_stmt = text(
                "SELECT bar_date, close "
                "FROM bars_1d "
                "WHERE symbol = :symbol "
                "ORDER BY bar_date DESC "
                "LIMIT 1"
            )
            latest_result = await session.execute(latest_stmt, {"symbol": ksym})
            latest_row = latest_result.mappings().first()
            latest_close = None
            latest_bar_date = None
            if latest_row is not None:
                latest_close = float(latest_row["close"])
                latest_bar_date = latest_row["bar_date"].isoformat() if hasattr(latest_row["bar_date"], "isoformat") else str(latest_row["bar_date"])
        except Exception as e:
            logger.warning("Cached status lookup failed for %s: %s", ksym, e)
            cached_bar_count = 0
            latest_close = None
            latest_bar_date = None

        return {
            "symbol": normalized,
            "kline_symbol": ksym,
            "symbol_mapping_ok": True,
            "cached_bars_available": cached_bar_count > 0,
            "cached_bar_count": cached_bar_count,
            "latest_cached_close": latest_close,
            "latest_cached_bar_date": latest_bar_date,
            "has_minimum_bars": cached_bar_count >= 200,
        }

    async def _fetch(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        self.upstream_fetches += 1
        try:
            df = self._provider.get_daily_bars(symbol, start, end, adjusted=True)
            if inspect.isawaitable(df):
                df = await df
            if df.empty:
                self.failed += 1
                return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"])
            self.latest_successful_fetch = datetime.now(timezone.utc)
            return df
        except Exception as e:
            self.failed += 1
            self._last_fetch_error = str(e)
            logger.error("KLine fetch failed for %s: %s", symbol, e)
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"])

    async def _load_cached(
        self, symbol: str, start: date, end: date, session: AsyncSession
    ) -> pd.DataFrame | None:
        try:
            columns = await self._bars_1d_columns(session)
            if not columns or "bar_date" not in columns or "close" not in columns:
                return None
            stmt = text(
                "SELECT bar_date, open, high, low, close, volume "
                "FROM bars_1d "
                "WHERE symbol = :symbol AND bar_date >= :start AND bar_date <= :end "
                "ORDER BY bar_date"
            )
            result = await session.execute(stmt, {"symbol": symbol, "start": start, "end": end})
            rows = result.mappings().all()
            if not rows:
                return None
            records = [
                {
                    "date": r["bar_date"],
                    "bar_date": r["bar_date"],
                    "open": r["open"],
                    "high": r["high"],
                    "low": r["low"],
                    "close": r["close"],
                    "volume": r["volume"],
                    "adj_close": r["close"],
                }
                for r in rows
            ]
            return pd.DataFrame(records)
        except Exception as e:
            logger.warning("Cache load failed for %s: %s", symbol, e)
            return None

    async def _write_cache(
        self, symbol: str, df: pd.DataFrame, session: AsyncSession
    ) -> None:
        try:
            columns = await self._bars_1d_columns(session)
            if not columns:
                return
            has_adj_close = "adj_close" in columns
            has_fetched_at = "fetched_at" in columns
            has_updated_at = "updated_at" in columns
            has_created_at = "created_at" in columns
            has_id = "id" in columns
            has_source = "source" in columns
            async with session.begin_nested():
                for _, row in df.iterrows():
                    bar_date = row["date"]
                    if hasattr(bar_date, "to_pydatetime"):
                        bar_date = bar_date.to_pydatetime().date()
                    elif hasattr(bar_date, "date"):
                        bar_date = bar_date.date()
                    elif isinstance(bar_date, str):
                        bar_date = date.fromisoformat(bar_date[:10])
                    now = datetime.now(timezone.utc)
                    existing_stmt = text(
                        "SELECT id FROM bars_1d WHERE symbol = :symbol AND bar_date = :bar_date LIMIT 1"
                    )
                    existing_result = await session.execute(existing_stmt, {"symbol": symbol, "bar_date": bar_date})
                    existing_row = existing_result.mappings().first()
                    values = {
                        "symbol": symbol,
                        "bar_date": bar_date,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                    }
                    if has_adj_close:
                        values["adj_close"] = float(row["adj_close"])
                    if has_fetched_at:
                        values["fetched_at"] = now
                    if has_updated_at:
                        values["updated_at"] = now
                    if has_created_at:
                        values["created_at"] = now
                    if has_id:
                        values["id"] = str(uuid4())
                    if has_source:
                        values["source"] = "yfinance"

                    if existing_row:
                        set_clauses = ["open = :open", "high = :high", "low = :low", "close = :close", "volume = :volume"]
                        if has_adj_close:
                            set_clauses.append("adj_close = :adj_close")
                        if has_fetched_at:
                            set_clauses.append("fetched_at = :fetched_at")
                        if has_updated_at:
                            set_clauses.append("updated_at = :updated_at")
                        if has_created_at:
                            set_clauses.append("created_at = COALESCE(created_at, :created_at)")
                        if has_source:
                            set_clauses.append("source = :source")
                        update_stmt = text(
                            f"UPDATE bars_1d SET {', '.join(set_clauses)} WHERE symbol = :symbol AND bar_date = :bar_date"
                        )
                        await session.execute(update_stmt, values)
                    else:
                        insert_columns = ["symbol", "bar_date", "open", "high", "low", "close", "volume"]
                        insert_values = [":symbol", ":bar_date", ":open", ":high", ":low", ":close", ":volume"]
                        if has_adj_close:
                            insert_columns.append("adj_close")
                            insert_values.append(":adj_close")
                        if has_fetched_at:
                            insert_columns.append("fetched_at")
                            insert_values.append(":fetched_at")
                        if has_updated_at:
                            insert_columns.append("updated_at")
                            insert_values.append(":updated_at")
                        if has_created_at:
                            insert_columns.append("created_at")
                            insert_values.append(":created_at")
                        if has_id:
                            insert_columns.append("id")
                            insert_values.append(":id")
                        if has_source:
                            insert_columns.append("source")
                            insert_values.append(":source")
                        insert_stmt = text(
                            f"INSERT INTO bars_1d ({', '.join(insert_columns)}) VALUES ({', '.join(insert_values)})"
                        )
                        await session.execute(insert_stmt, values)
        except Exception as e:
            bar_count = len(df) if df is not None else 0
            first_date = str(df["date"].iloc[0]) if df is not None and not df.empty and "date" in df.columns else None
            last_date = str(df["date"].iloc[-1]) if df is not None and not df.empty and "date" in df.columns else None
            logger.error(
                "Cache write failed | stage=kline_cache_write symbol=%s provider=%s bar_count=%s first_date=%s last_date=%s error=%s",
                symbol, self._provider.__class__.__name__, bar_count, first_date, last_date, e,
            )

    def _track(self, symbol: str, bars: int, source: str, last_error: str | None = None) -> None:
        self._per_symbol[symbol] = {
            "bars": bars,
            "source": source,
            "last_error": last_error,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _coerce_date(value) -> date | None:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    def get_status(self) -> dict:
        return {
            "provider": settings.kline_provider,
            "cache_enabled": self._enable_cache,
            "lookback_days": settings.kline_lookback_days,
            "extended_lookback_days": settings.kline_extended_lookback_days,
            "requests": self.requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "upstream_fetches": self.upstream_fetches,
            "failed": self.failed,
            "latest_successful_fetch": self.latest_successful_fetch.isoformat() if self.latest_successful_fetch else None,
            "per_symbol": dict(self._per_symbol),
        }
