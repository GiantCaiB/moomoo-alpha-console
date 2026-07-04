from types import SimpleNamespace

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_broker, get_kline_service, get_runtime_state
from app.core.config import settings
from app.db.session import get_session
from app.services.kline.symbol_map import normalize_symbol
from app.services.market_data.price_resolver import PriceResolver
from app.services.settings.trading_universe import TradingUniverseResolver

router = APIRouter()


def _to_moomoo_symbol(symbol: str) -> str:
    if "." in symbol:
        return symbol
    return f"US.{symbol}"


@router.get("/api/v1/diagnostics/signal-pipeline")
async def signal_pipeline_diagnostics(
    symbols: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    runtime_state_error = None
    try:
        runtime_state = await get_runtime_state().build(session)
    except Exception as exc:
        runtime_state_error = str(exc)
        runtime_state = SimpleNamespace(
            broker_mode=settings.broker_mode.lower(),
            read_only=True,
            broker_adapter="Unavailable",
            account_environment="unknown",
            trading_universe=TradingUniverseResolver.get_default_symbols(),
            trading_universe_source="default",
            kline_provider=settings.kline_provider,
            kline_cache_enabled=True,
            signal_data_source="moomoo_snapshot_plus_yfinance_kline" if settings.broker_mode.lower() == "moomoo" else "local_generated",
            mock_enabled=settings.broker_mode.lower() != "moomoo",
            price_source_priority=["moomoo_quote_last_price", "moomoo_position_current_price", "yfinance_cached_latest_close", "DATA_ERROR"],
            signal_provider="MoomooMomentumResearchProvider" if settings.broker_mode.lower() == "moomoo" else "LocalMomentumResearchProvider",
        )

    try:
        broker = get_broker()
    except Exception:
        broker = None

    try:
        kline_service = get_kline_service()
    except Exception:
        kline_service = None

    price_resolver = PriceResolver(broker=broker, kline_service=kline_service) if broker is not None and kline_service is not None else None

    requested_symbols = symbols or runtime_state.trading_universe
    diagnostics: list[dict] = []

    for raw_symbol in requested_symbols:
        normalized = normalize_symbol(raw_symbol)
        symbol_name = normalized or raw_symbol
        row = {
            "symbol": symbol_name,
            "moomoo_symbol": _to_moomoo_symbol(symbol_name) if normalized else None,
            "moomoo_quote_attempted": False,
            "moomoo_quote_success": False,
            "moomoo_quote_price": None,
            "moomoo_quote_error": None,
            "position_price_available": False,
            "position_price": None,
            "kline_fetch_attempted": False,
            "kline_bars_count": 0,
            "cached_bars_count": 0,
            "latest_cached_close": None,
            "latest_cached_bar_date": None,
            "latest_bar_from_current_fetch": None,
            "price_resolver_used_bars_fallback": False,
            "final_price_source": "DATA_ERROR",
            "final_price": None,
            "final_error": None,
        }
        if runtime_state_error is not None:
            row["runtime_state_error"] = runtime_state_error

        try:
            if normalized is None:
                row["moomoo_quote_error"] = "invalid_symbol"
                row["final_error"] = "invalid_symbol"
                diagnostics.append(row)
                continue

            if kline_service is None:
                row["final_error"] = runtime_state_error or "KLineService not initialized"
                diagnostics.append(row)
                continue

            try:
                kline_result = await kline_service.get_cached_or_fetch_daily_bars(normalized, session=session)
                row["kline_fetch_attempted"] = True
                row["kline_bars_count"] = len(kline_result.bars)
                row["latest_cached_close"] = kline_result.latest_cached_close
                row["latest_cached_bar_date"] = kline_result.latest_cached_bar_date
                row["latest_bar_from_current_fetch"] = kline_result.latest_bar_from_current_fetch
                if kline_result.bars.empty and kline_result.fetch_failed:
                    row["final_error"] = kline_result.fetch_error or "No price data available"
            except Exception as exc:
                row["kline_fetch_attempted"] = True
                row["final_error"] = str(exc)
                diagnostics.append(row)
                continue

            try:
                if normalized.upper() != "SPY" and broker is not None:
                    row["moomoo_quote_attempted"] = True
                    quote = await broker.get_quote(normalized)
                    row["moomoo_quote_success"] = quote.last is not None and quote.last > 0
                    row["moomoo_quote_price"] = float(quote.last) if quote.last is not None and quote.last > 0 else None
                    row["moomoo_quote_error"] = None if row["moomoo_quote_success"] else "quote_missing"
                    positions = await broker.get_positions()
                    for position in positions:
                        if position.symbol.upper() == normalized.upper() and position.current_price is not None and position.current_price > 0:
                            row["position_price_available"] = True
                            row["position_price"] = float(position.current_price)
                            break
            except Exception as exc:
                row["final_error"] = str(exc)
                diagnostics.append(row)
                continue

            try:
                if price_resolver is not None:
                    price_resolution = await price_resolver.resolve(normalized, bars=kline_result.bars, session=session)
                    row["price_resolver_used_bars_fallback"] = price_resolution.price_resolver_used_bars_fallback
                    row["final_price_source"] = price_resolution.price_source
                    row["final_price"] = price_resolution.price
                    if row["final_error"] is None:
                        row["final_error"] = price_resolution.error or (
                            None if price_resolution.price is not None else "No price data available"
                        )
                elif not kline_result.bars.empty:
                    latest_close = kline_result.latest_cached_close
                    row["price_resolver_used_bars_fallback"] = True
                    row["final_price_source"] = "yfinance_cached_latest_close"
                    row["final_price"] = latest_close
                else:
                    row["final_error"] = row["final_error"] or "PriceResolver not initialized"
            except Exception as exc:
                row["final_error"] = str(exc)
                diagnostics.append(row)
                continue

            row["cached_bars_count"] = kline_service.get_status().get("per_symbol", {}).get(normalized, {}).get("bars", 0)
            diagnostics.append(row)
        except Exception as exc:
            row["final_error"] = str(exc)
            diagnostics.append(row)

    return {
        "broker_adapter": runtime_state.broker_adapter,
        "price_source_priority": runtime_state.price_source_priority,
        "kline_provider": runtime_state.kline_provider,
        "signal_provider": runtime_state.signal_provider,
        "trading_universe_source": runtime_state.trading_universe_source,
        "mock_enabled": runtime_state.mock_enabled,
        "read_only": runtime_state.read_only,
        "symbols": diagnostics,
    }
