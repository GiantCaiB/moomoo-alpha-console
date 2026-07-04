import re
from dataclasses import dataclass


INVALID_SYMBOLS = {"MOOMOO", "YFINANCE", "MOOMOO_REAL", "MOOMOO_READ_ONLY"}


@dataclass
class KlineSymbolInfo:
    requested_symbol: str
    kline_symbol: str
    proxy_used: bool = False
    proxy_reason: str | None = None


def normalize_symbol(raw: str | None) -> str | None:
    if raw is None:
        return None

    symbol = str(raw).strip()
    if not symbol:
        return None

    upper = symbol.upper()
    if upper in INVALID_SYMBOLS:
        return None

    if not re.fullmatch(r"[A-Z0-9-]{1,10}", upper):
        return None

    return upper


def to_kline_symbol(raw: str) -> KlineSymbolInfo:
    normalized = normalize_symbol(raw)
    if normalized is None:
        return KlineSymbolInfo(
            requested_symbol=raw,
            kline_symbol="",
            proxy_used=False,
            proxy_reason="invalid_symbol",
        )
    if "." in normalized:
        parts = normalized.split(".", 1)
        return KlineSymbolInfo(
            requested_symbol=normalized,
            kline_symbol=parts[1],
            proxy_used=False,
        )
    return KlineSymbolInfo(
        requested_symbol=normalized,
        kline_symbol=normalized,
        proxy_used=False,
    )
