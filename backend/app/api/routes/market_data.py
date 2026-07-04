from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_broker, get_kline_service, get_runtime_state
from app.core.config import settings
from app.db.session import get_session
from app.services.kline.symbol_map import normalize_symbol
from app.services.market_data.price_resolver import PriceResolver

router = APIRouter(tags=["market-data"])


def _to_moomoo_symbol(symbol: str) -> str:
    if "." in symbol:
        return symbol
    return f"{settings.moomoo_market.upper()}.{symbol}"


@router.get("/api/v1/market-data/status")
async def market_data_status(
    symbols: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    kline = get_kline_service()
    runtime_state = await get_runtime_state().build(session)
    response = {
        **kline.get_status(),
        "broker_mode": runtime_state.broker_mode,
        "read_only": runtime_state.read_only,
        "broker_adapter": runtime_state.broker_adapter,
        "account_environment": runtime_state.account_environment,
        "trading_universe": runtime_state.trading_universe,
        "trading_universe_source": runtime_state.trading_universe_source,
        "signal_data_source": runtime_state.signal_data_source,
        "mock_enabled": runtime_state.mock_enabled,
        "price_source_priority": runtime_state.price_source_priority,
    }

    if not symbols:
        return response

    broker = get_broker()
    price_resolver = PriceResolver(broker=broker, kline_service=kline)
    universe = set(runtime_state.trading_universe)
    broker_health = await broker.health_check()
    rows: list[dict] = []

    for raw_symbol in symbols:
        normalized = normalize_symbol(raw_symbol)
        if normalized is None:
            rows.append({
                "symbol": raw_symbol,
                "moomoo_quote_attempted": False,
                "moomoo_symbol": None,
                "moomoo_quote_success": False,
                "quote_price": None,
                "moomoo_quote_return_value": None,
                "moomoo_quote_error": "invalid_symbol",
                "cached_bars": False,
                "cached_bar_count": 0,
                "latest_close": None,
                "latest_cached_bar_date": None,
                "final_price_source": "DATA_ERROR",
                "final_price": None,
                "error": "invalid_symbol",
            })
            continue

        quote = await broker.get_quote(normalized)
        quote_price = quote.last if quote.last is not None and quote.last > 0 else None
        price_resolution = await price_resolver.resolve(normalized, session=session)
        kline_status = await kline.get_symbol_status(normalized, session=session)
        quote_error = None if quote_price is not None else broker_health.message or "quote_missing"

        rows.append({
            "symbol": normalized,
            "requested_symbol": raw_symbol,
            "in_trading_universe": normalized in universe,
            "moomoo_quote_attempted": True,
            "moomoo_symbol": _to_moomoo_symbol(normalized),
            "moomoo_quote_success": quote_price is not None,
            "quote_price": quote_price,
            "moomoo_quote_return_value": {
                "bid": quote.bid,
                "ask": quote.ask,
                "last": quote.last,
                "volume": quote.volume,
                "timestamp": quote.timestamp.isoformat() if getattr(quote, "timestamp", None) else None,
            },
            "moomoo_quote_error": None if quote_price is not None else quote_error,
            "cached_bars": kline_status["cached_bars_available"],
            "cached_bar_count": kline_status["cached_bar_count"],
            "latest_close": kline_status["latest_cached_close"],
            "latest_cached_bar_date": kline_status["latest_cached_bar_date"],
            "final_price_source": price_resolution.price_source,
            "final_price": price_resolution.price,
            "error": price_resolution.error,
        })

    response["symbols"] = rows
    return response
