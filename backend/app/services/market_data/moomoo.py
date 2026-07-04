"""
Moomoo Market Data Provider.

Fetches real-time quotes from moomoo OpenD.
Historical daily bars are NOT provided here — use KLineService instead.
No mock fallback — fails clearly when data is unavailable.
"""
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import moomoo as ft
    MOOMOO_SDK_AVAILABLE = True
except Exception:
    ft = None
    MOOMOO_SDK_AVAILABLE = False


def _to_moomoo_symbol(symbol: str) -> str:
    if "." in symbol:
        return symbol
    market = settings.moomoo_market.upper()
    return f"{market}.{symbol}"


def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class MoomooMarketDataProvider:
    def __init__(self) -> None:
        self._error: str | None = None

    @property
    def available(self) -> bool:
        return MOOMOO_SDK_AVAILABLE

    @property
    def error(self) -> str | None:
        return self._error

    async def get_quote(self, symbol: str) -> dict:
        if not MOOMOO_SDK_AVAILABLE:
            self._error = "Moomoo SDK not installed"
            return {"symbol": symbol, "last": None, "bid": None, "ask": None, "volume": None}

        moomoo_sym = _to_moomoo_symbol(symbol)
        try:
            quote_ctx = ft.OpenQuoteContext(
                host=settings.moomoo_host,
                port=settings.moomoo_port,
            )
            ret, data = quote_ctx.get_stock_quote([moomoo_sym])
            quote_ctx.close()

            if ret != ft.RET_OK or data is None or len(data) == 0:
                self._error = f"No quote data for {symbol}"
                return {"symbol": symbol, "last": None, "bid": None, "ask": None, "volume": None}

            row = data.iloc[0] if hasattr(data, "iloc") else data[0]
            return {
                "symbol": symbol,
                "last": _safe_float(row.get("last_price")) or None,
                "bid": _safe_float(row.get("bid_price")) or None,
                "ask": _safe_float(row.get("ask_price")) or None,
                "volume": _safe_float(row.get("volume")) or None,
            }
        except Exception as e:
            self._error = f"Quote fetch failed for {symbol}: {e}"
            logger.error(self._error)
            return {"symbol": symbol, "last": None, "bid": None, "ask": None, "volume": None}
