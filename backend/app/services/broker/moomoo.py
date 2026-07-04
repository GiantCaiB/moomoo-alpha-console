"""
Moomoo / Futu OpenAPI broker adapter — READ-ONLY PHASE.

This adapter reads account data, positions, open orders, and quotes
from moomoo OpenD. It NEVER places or cancels orders in this phase.

Safety rules (enforced at code level):
  1. place_limit_order()  → raises RuntimeError("Read-only")
  2. cancel_order()       → raises RuntimeError("Read-only")
  3. TRADING_ENABLED is ignored for write gating — writes always fail.
  4. MOOMOO_TRD_ENV controls which environment to read:
       SIMULATE → simulated account (no real money)
       REAL     → real account (real money, read-only)

Usage:
  - Set BROKER_MODE=moomoo
  - Set MOOMOO_TRD_ENV=SIMULATE or REAL
  - Ensure OpenD is running on MOOMOO_HOST:MOOMOO_PORT
"""
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.broker.base import (
    AccountSummary,
    PositionDto,
    OrderDto,
    QuoteDto,
    LimitOrderRequest,
    BrokerHealth,
)

logger = logging.getLogger(__name__)

try:
    import moomoo as ft
    MOOMOO_SDK_AVAILABLE = True
except Exception:
    ft = None
    MOOMOO_SDK_AVAILABLE = False
    logger.warning("Moomoo SDK not installed. MoomooBrokerAdapter will be unavailable.")


# ---------------------------------------------------------------------------
# Symbol mapping helpers
# ---------------------------------------------------------------------------

def _to_moomoo_symbol(symbol: str) -> str:
    """Convert internal symbol (AAPL) → moomoo format (US.AAPL)."""
    if "." in symbol:
        return symbol
    market = settings.moomoo_market.upper()
    return f"{market}.{symbol}"


def _from_moomoo_symbol(code: str) -> str:
    """Convert moomoo format (US.AAPL) → internal symbol (AAPL)."""
    prefix = f"{settings.moomoo_market.upper()}."
    return code[len(prefix):] if code.startswith(prefix) else code


# ---------------------------------------------------------------------------
# Order status mapping (moomoo SDK returns string statuses)
# ---------------------------------------------------------------------------

_MOOMOO_STATUS_MAP: dict[str, str] = {
    "N/A": "PENDING",
    "UNSUBMITTED": "PENDING",
    "WAITING_SUBMIT": "PENDING",
    "SUBMITTING": "SUBMITTING",
    "SUBMIT_FAILED": "REJECTED",
    "TIMEOUT": "FAILED",
    "SUBMITTED": "SUBMITTED",
    "FILLED_PART": "PARTIALLY_FILLED",
    "FILLED_ALL": "FILLED",
    "CANCELLING_PART": "CANCELLING",
    "CANCELLING_ALL": "CANCELLING",
    "CANCELLED_PART": "CANCELLED",
    "CANCELLED_ALL": "CANCELLED",
    "FAILED": "REJECTED",
    "DISABLED": "DISABLED",
    "DELETED": "CANCELLED",
    "FILL_CANCELLED": "CANCELLED",
}


def _map_order_status(status_str: str) -> str:
    return _MOOMOO_STATUS_MAP.get(status_str, "UNKNOWN")


# ---------------------------------------------------------------------------
# Trade environment resolution
# ---------------------------------------------------------------------------

def _resolve_trd_env() -> Any:
    """Resolve TrdEnv value from settings."""
    s = settings.moomoo_trd_env.upper().strip()
    if not MOOMOO_SDK_AVAILABLE:
        return s
    if s == "REAL":
        return ft.TrdEnv.REAL
    return ft.TrdEnv.SIMULATE


# ---------------------------------------------------------------------------
# Market mapping
# ---------------------------------------------------------------------------

_MARKET_MAP: dict[str, Any] = {}
if MOOMOO_SDK_AVAILABLE:
    _MARKET_MAP = {
        "US": ft.TrdMarket.US,
        "HK": ft.TrdMarket.HK,
        "CN": ft.TrdMarket.CN,
        "SG": ft.TrdMarket.SG,
        "AU": ft.TrdMarket.AU,
        "JP": ft.TrdMarket.JP,
        "CA": ft.TrdMarket.CA,
        "MY": ft.TrdMarket.MY,
    }


def _resolve_market() -> Any:
    m = settings.moomoo_market.upper().strip()
    return _MARKET_MAP.get(m, None)


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------

def _series_get(row: Any, key: str, default: Any = None) -> Any:
    """Get a value from a pandas Series, returning default if missing."""
    if hasattr(row, "get"):
        val = row.get(key)
        return val if val is not None else default
    return getattr(row, key, default)


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class MoomooBrokerAdapter:
    def __init__(self) -> None:
        self._connected = False
        self._ctx: Any = None
        self._error: str | None = None
        self._account_id: int | None = None
        self._trd_env: Any = None

    async def connect(self) -> None:
        if not MOOMOO_SDK_AVAILABLE:
            self._error = "Moomoo SDK not installed. Install with: pip install moomoo-api"
            logger.error(self._error)
            self._connected = False
            return

        self._trd_env = _resolve_trd_env()
        env_label = "SIMULATE" if self._trd_env == ft.TrdEnv.SIMULATE else "REAL"

        filter_market = _resolve_market()
        if filter_market is None:
            self._error = f"Unsupported moomoo_market: {settings.moomoo_market}"
            logger.error(self._error)
            self._connected = False
            return

        logger.info(
            "Connecting to OpenD at %s:%s (trd_env=%s, market=%s)",
            settings.moomoo_host, settings.moomoo_port, env_label, filter_market,
        )

        try:
            self._ctx = ft.OpenSecTradeContext(
                filter_trdmarket=filter_market,
                host=settings.moomoo_host,
                port=settings.moomoo_port,
            )
            self._ctx.start()
            self._connected = True
            self._error = None
            logger.info("Moomoo adapter connected (trd_env=%s)", env_label)
        except Exception as e:
            self._connected = False
            self._error = f"Connection failed: {e}"
            logger.error(self._error)

    async def disconnect(self) -> None:
        self._connected = False
        if self._ctx is not None:
            try:
                self._ctx.close()
            except Exception:
                pass
            self._ctx = None
        logger.info("Moomoo adapter disconnected")

    async def health_check(self) -> BrokerHealth:
        if not MOOMOO_SDK_AVAILABLE:
            return BrokerHealth(
                connected=False,
                latency_ms=None,
                message="SDK not installed",
            )
        if not self._connected or self._ctx is None:
            return BrokerHealth(
                connected=False,
                latency_ms=None,
                message=self._error or "Not connected",
            )
        try:
            t0 = time.monotonic()
            ret, _ = self._ctx.get_acc_list()
            elapsed = (time.monotonic() - t0) * 1000
            if ret == ft.RET_OK:
                return BrokerHealth(
                    connected=True,
                    latency_ms=round(elapsed, 1),
                    message="Connected",
                )
            return BrokerHealth(
                connected=False,
                latency_ms=round(elapsed, 1),
                message="OpenD returned error",
            )
        except Exception as e:
            return BrokerHealth(
                connected=False,
                latency_ms=None,
                message=str(e),
            )

    async def _ensure_account_id(self) -> int | None:
        """Fetch and cache the account ID matching the current trd_env."""
        if self._account_id is not None:
            return self._account_id
        try:
            ret, acc_list = self._ctx.get_acc_list()
            if ret != ft.RET_OK or acc_list is None or len(acc_list) == 0:
                logger.warning("Moomoo: no accounts found")
                return None

            trd_env_str = "SIMULATE" if self._trd_env == ft.TrdEnv.SIMULATE else "REAL"
            for _, row in acc_list.iterrows():
                if str(row.get("trd_env", "")).upper() == trd_env_str:
                    self._account_id = _safe_int(row.get("acc_id"))
                    logger.info("Moomoo: using %s account acc_id=%s", trd_env_str, self._account_id)
                    return self._account_id

            logger.warning("Moomoo: no %s account found, falling back to first", trd_env_str)
            row = acc_list.iloc[0]
            self._account_id = _safe_int(row.get("acc_id"))
            return self._account_id
        except Exception as e:
            logger.error("Moomoo _ensure_account_id error: %s", e)
            return None

    async def get_account(self) -> AccountSummary:
        if not MOOMOO_SDK_AVAILABLE or not self._connected or self._ctx is None:
            logger.warning("Moomoo get_account: not available")
            return AccountSummary(
                total_value=0.0, cash=0.0, positions_value=0.0,
                day_pnl=0.0, day_pnl_pct=0.0, total_pnl=0.0, total_pnl_pct=0.0,
                drawdown_pct=0.0, buying_power=0.0, currency="USD",
            )
        try:
            acc_id = await self._ensure_account_id()
            if acc_id is None:
                raise RuntimeError("No accounts")

            ret2, info = self._ctx.accinfo_query(
                trd_env=self._trd_env,
                acc_id=acc_id,
                currency=ft.Currency.USD,
            )
            if ret2 != ft.RET_OK or info is None or len(info) == 0:
                raise RuntimeError("accinfo_query failed")

            row = info.iloc[0]
            total = _safe_float(_series_get(row, "total_assets"))
            cash = _safe_float(_series_get(row, "cash"))
            bp = _safe_float(_series_get(row, "power"))
            pos_val = _safe_float(_series_get(row, "market_val"))
            unrealized_pnl = _safe_float(_series_get(row, "unrealized_pl"))

            return AccountSummary(
                total_value=round(total, 2),
                cash=round(cash, 2),
                positions_value=round(pos_val, 2),
                day_pnl=0.0,
                day_pnl_pct=0.0,
                total_pnl=round(unrealized_pnl, 2),
                total_pnl_pct=round((unrealized_pnl / total * 100) if total > 0 else 0.0, 2),
                drawdown_pct=0.0,
                buying_power=round(bp, 2),
                currency="USD",
            )
        except Exception as e:
            logger.error("Moomoo get_account error: %s", e)
            return AccountSummary(
                total_value=0.0, cash=0.0, positions_value=0.0,
                day_pnl=0.0, day_pnl_pct=0.0, total_pnl=0.0, total_pnl_pct=0.0,
                drawdown_pct=0.0, buying_power=0.0, currency="USD",
            )

    async def get_positions(self) -> list[PositionDto]:
        if not MOOMOO_SDK_AVAILABLE or not self._connected or self._ctx is None:
            return []
        try:
            acc_id = await self._ensure_account_id()
            if acc_id is None:
                return []

            ret2, pos_list = self._ctx.position_list_query(
                trd_env=self._trd_env,
                acc_id=acc_id,
                currency=ft.Currency.USD,
            )
            if ret2 != ft.RET_OK or pos_list is None or len(pos_list) == 0:
                return []

            positions: list[PositionDto] = []
            for _, p in pos_list.iterrows():
                symbol = _from_moomoo_symbol(str(_series_get(p, "code", "")))
                qty = _safe_int(_series_get(p, "qty"))
                cost = _safe_float(_series_get(p, "cost_price"))
                price = _safe_float(_series_get(p, "nominal_price"))
                market_val = _safe_float(_series_get(p, "market_val"))
                pl_val = _safe_float(_series_get(p, "pl_val"))
                pl_ratio = _safe_float(_series_get(p, "pl_ratio"))

                total_val = _safe_float((await self.get_account()).total_value)
                pct = round(market_val / total_val * 100, 2) if total_val > 0 else 0.0

                positions.append(PositionDto(
                    symbol=symbol,
                    quantity=qty,
                    avg_cost=round(cost, 2),
                    current_price=round(price, 2) if price else None,
                    unrealized_pnl=round(pl_val, 2),
                    day_pnl=round(pl_ratio, 2) if pl_ratio else None,
                    stop_level=None,
                    position_pct=pct,
                ))
            return positions
        except Exception as e:
            logger.error("Moomoo get_positions error: %s", e)
            return []

    async def get_open_orders(self) -> list[OrderDto]:
        if not MOOMOO_SDK_AVAILABLE or not self._connected or self._ctx is None:
            return []
        try:
            acc_id = await self._ensure_account_id()
            if acc_id is None:
                return []

            ret2, order_list = self._ctx.order_list_query(
                trd_env=self._trd_env,
                acc_id=acc_id,
            )
            if ret2 != ft.RET_OK or order_list is None or len(order_list) == 0:
                return []

            orders: list[OrderDto] = []
            for _, o in order_list.iterrows():
                status_str = str(_series_get(o, "order_status", ""))
                side_str = str(_series_get(o, "trd_side", ""))
                side = "BUY" if side_str == "BUY" else "SELL"

                orders.append(OrderDto(
                    order_id=str(_series_get(o, "order_id", "")),
                    symbol=_from_moomoo_symbol(str(_series_get(o, "code", ""))),
                    side=side,
                    order_type="LIMIT",
                    quantity=_safe_int(_series_get(o, "qty")),
                    filled_quantity=_safe_int(_series_get(o, "dealt_qty")),
                    limit_price=_safe_float(_series_get(o, "price")) or None,
                    stop_price=None,
                    status=_map_order_status(status_str),
                    reason=None,
                    created_at=datetime.now(timezone.utc),
                    submitted_at=datetime.now(timezone.utc),
                    filled_at=None,
                    cancelled_at=None,
                ))
            return orders
        except Exception as e:
            logger.error("Moomoo get_open_orders error: %s", e)
            return []

    async def get_quote(self, symbol: str) -> QuoteDto:
        if not MOOMOO_SDK_AVAILABLE or not self._connected:
            return QuoteDto(
                symbol=symbol, bid=None, ask=None, last=None,
                volume=None, bid_size=None, ask_size=None,
                timestamp=datetime.now(timezone.utc),
            )
        try:
            moomoo_sym = _to_moomoo_symbol(symbol)
            quote_ctx = ft.OpenQuoteContext(
                host=settings.moomoo_host,
                port=settings.moomoo_port,
            )
            ret, data = quote_ctx.get_stock_quote([moomoo_sym])
            quote_ctx.close()

            if ret != ft.RET_OK or data is None or len(data) == 0:
                return QuoteDto(
                    symbol=symbol, bid=None, ask=None, last=None,
                    volume=None, bid_size=None, ask_size=None,
                    timestamp=datetime.now(timezone.utc),
                )

            row = data.iloc[0] if hasattr(data, "iloc") else data[0]
            now = datetime.now(timezone.utc)

            return QuoteDto(
                symbol=symbol,
                bid=_safe_float(_series_get(row, "bid_price")) or None,
                ask=_safe_float(_series_get(row, "ask_price")) or None,
                last=_safe_float(_series_get(row, "last_price")) or None,
                volume=_safe_float(_series_get(row, "volume")) or None,
                bid_size=_safe_int(_series_get(row, "bid_size")) or None,
                ask_size=_safe_int(_series_get(row, "ask_size")) or None,
                timestamp=now,
            )
        except Exception as e:
            logger.error("Moomoo get_quote error for %s: %s", symbol, e)
            return QuoteDto(
                symbol=symbol, bid=None, ask=None, last=None,
                volume=None, bid_size=None, ask_size=None,
                timestamp=datetime.now(timezone.utc),
            )

    async def place_limit_order(self, request: LimitOrderRequest) -> OrderDto:
        """Always fails closed in read-only phase."""
        raise RuntimeError(
            "Read-only mode: order placement disabled. "
            "Live trading is not implemented in this phase."
        )

    async def cancel_order(self, order_id: str) -> None:
        """Always fails closed in read-only phase."""
        raise RuntimeError(
            "Read-only mode: order cancellation disabled. "
            "Live trading is not implemented in this phase."
        )
