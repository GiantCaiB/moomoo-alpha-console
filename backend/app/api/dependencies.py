"""
Shared dependencies for FastAPI route injection.

Keeps shared singletons in a separate module
to avoid circular imports between app.main and app.api.routes.*
"""
from app.services.broker.base import BrokerAdapter
from app.services.risk.engine import RiskEngine
from app.services.market_data.moomoo import MoomooMarketDataProvider as DefaultMarketDataProvider
from app.services.runtime.state import RuntimeStateService
from app.services.settings.trading_universe import TradingUniverseResolver
from app.services.market_data.price_resolver import PriceResolver

_broker: BrokerAdapter | None = None
_risk_engine: RiskEngine | None = None
_market_data: DefaultMarketDataProvider | None = None
_kline_service: object | None = None
_runtime_state: RuntimeStateService | None = None
_trading_universe_resolver: TradingUniverseResolver | None = None
_price_resolver: PriceResolver | None = None


def set_broker(broker: BrokerAdapter) -> None:
    global _broker
    _broker = broker


def set_risk_engine(engine: RiskEngine) -> None:
    global _risk_engine
    _risk_engine = engine


def set_market_data(provider: DefaultMarketDataProvider) -> None:
    global _market_data
    _market_data = provider


def set_kline_service(service: object) -> None:
    global _kline_service
    _kline_service = service


def set_runtime_state(service: RuntimeStateService) -> None:
    global _runtime_state
    _runtime_state = service


def set_trading_universe_resolver(resolver: TradingUniverseResolver) -> None:
    global _trading_universe_resolver
    _trading_universe_resolver = resolver


def set_price_resolver(resolver: PriceResolver) -> None:
    global _price_resolver
    _price_resolver = resolver


def get_broker() -> BrokerAdapter:
    if _broker is None:
        raise RuntimeError("Broker not initialized")
    return _broker


def get_risk_engine() -> RiskEngine:
    if _risk_engine is None:
        raise RuntimeError("Risk engine not initialized")
    return _risk_engine


def get_market_data() -> DefaultMarketDataProvider:
    if _market_data is None:
        raise RuntimeError("Market data provider not initialized")
    return _market_data


def get_kline_service():
    if _kline_service is None:
        raise RuntimeError("KLineService not initialized")
    return _kline_service


def get_runtime_state() -> RuntimeStateService:
    if _runtime_state is None:
        raise RuntimeError("RuntimeStateService not initialized")
    return _runtime_state


def get_trading_universe_resolver() -> TradingUniverseResolver:
    if _trading_universe_resolver is None:
        raise RuntimeError("TradingUniverseResolver not initialized")
    return _trading_universe_resolver


def get_price_resolver() -> PriceResolver:
    if _price_resolver is None:
        raise RuntimeError("PriceResolver not initialized")
    return _price_resolver
