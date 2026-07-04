from dataclasses import dataclass

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.broker.base import BrokerAdapter
from app.services.kline.service import KLineService


@dataclass(frozen=True)
class PriceResolution:
    symbol: str
    price: float | None
    price_source: str
    price_timestamp: str | None
    price_is_realtime: bool
    price_resolver_used_bars_fallback: bool
    moomoo_quote_available: bool
    moomoo_quote_price: float | None
    moomoo_position_available: bool
    moomoo_position_price: float | None
    latest_cached_close: float | None
    cached_bars_available: bool
    error: str | None


class PriceResolver:
    def __init__(self, broker: BrokerAdapter, kline_service: KLineService) -> None:
        self._broker = broker
        self._kline = kline_service

    async def resolve(
        self,
        symbol: str,
        bars: pd.DataFrame | None = None,
        session: AsyncSession | None = None,
    ) -> PriceResolution:
        quote = await self._broker.get_quote(symbol)
        quote_price = self._safe_price(quote.last)
        if quote_price is not None:
            return PriceResolution(
                symbol=symbol,
                price=quote_price,
                price_source="moomoo_quote_last_price",
                price_timestamp=self._quote_timestamp(quote),
                price_is_realtime=True,
                price_resolver_used_bars_fallback=False,
                moomoo_quote_available=True,
                moomoo_quote_price=quote_price,
                moomoo_position_available=False,
                moomoo_position_price=None,
                latest_cached_close=None,
                cached_bars_available=False,
                error=None,
            )

        positions = await self._broker.get_positions()
        position_price = None
        for position in positions:
            if position.symbol.upper() == symbol.upper():
                position_price = self._safe_price(position.current_price)
                break

        if position_price is not None:
            return PriceResolution(
                symbol=symbol,
                price=position_price,
                price_source="moomoo_position_current_price",
                price_timestamp=None,
                price_is_realtime=True,
                price_resolver_used_bars_fallback=False,
                moomoo_quote_available=False,
                moomoo_quote_price=None,
                moomoo_position_available=True,
                moomoo_position_price=position_price,
                latest_cached_close=None,
                cached_bars_available=False,
                error=None,
            )

        latest_close, price_timestamp = self._latest_price_from_bars(bars)
        if latest_close is None:
            latest_close = await self._kline.get_latest_cached_close(symbol, session=session)
            price_timestamp = None
        if latest_close is not None:
            return PriceResolution(
                symbol=symbol,
                price=latest_close,
                price_source="yfinance_cached_latest_close",
                price_timestamp=price_timestamp,
                price_is_realtime=False,
                price_resolver_used_bars_fallback=bars is not None and not bars.empty,
                moomoo_quote_available=False,
                moomoo_quote_price=None,
                moomoo_position_available=False,
                moomoo_position_price=None,
                latest_cached_close=latest_close,
                cached_bars_available=True,
                error=None,
            )

        return PriceResolution(
            symbol=symbol,
            price=None,
            price_source="DATA_ERROR",
            price_timestamp=None,
            price_is_realtime=False,
            price_resolver_used_bars_fallback=bars is not None and not bars.empty,
            moomoo_quote_available=False,
            moomoo_quote_price=None,
            moomoo_position_available=False,
            moomoo_position_price=None,
            latest_cached_close=None,
            cached_bars_available=False,
            error="No price data available",
        )

    @staticmethod
    def _safe_price(value: float | None) -> float | None:
        if value is None:
            return None
        try:
            price = float(value)
        except (TypeError, ValueError):
            return None
        return price if price > 0 else None

    @staticmethod
    def _quote_timestamp(quote) -> str | None:
        timestamp = getattr(quote, "timestamp", None)
        if timestamp is None:
            return None
        if hasattr(timestamp, "isoformat"):
            return timestamp.isoformat()
        return str(timestamp)

    @staticmethod
    def _latest_price_from_bars(bars: pd.DataFrame | None) -> tuple[float | None, str | None]:
        if bars is None or bars.empty:
            return None, None
        date_column = "date" if "date" in bars.columns else "bar_date" if "bar_date" in bars.columns else None
        if date_column is None:
            return None, None
        close_column = "adj_close" if "adj_close" in bars.columns else "close" if "close" in bars.columns else None
        if close_column is None:
            return None, None

        valid_rows = bars[bars[close_column].notna()]
        if valid_rows.empty:
            return None, None
        valid_rows = valid_rows[valid_rows[close_column].astype(float) > 0]
        if valid_rows.empty:
            return None, None
        latest_row = valid_rows.iloc[-1]
        try:
            price = float(latest_row[close_column])
        except (TypeError, ValueError):
            return None, None
        timestamp = latest_row[date_column]
        if hasattr(timestamp, "isoformat"):
            timestamp = timestamp.isoformat()
        else:
            timestamp = str(timestamp)
        return price, timestamp
