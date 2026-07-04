from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.broker.base import BrokerAdapter
from app.services.broker.safety import compute_broker_safety_state
from app.services.settings.trading_universe import TradingUniverseResolver


@dataclass(frozen=True)
class RuntimeState:
    broker_mode: str
    read_only: bool
    broker_adapter: str
    account_environment: str
    trading_universe: list[str]
    trading_universe_source: str
    kline_provider: str
    kline_cache_enabled: bool
    signal_data_source: str
    mock_enabled: bool
    price_source_priority: list[str]
    signal_provider: str


class RuntimeStateService:
    def __init__(
        self,
        broker: BrokerAdapter,
        kline_service,
        trading_universe_resolver: TradingUniverseResolver,
    ) -> None:
        self._broker = broker
        self._kline_service = kline_service
        self._universe_resolver = trading_universe_resolver

    async def build(self, session: AsyncSession) -> RuntimeState:
        broker_health = await self._broker.health_check()
        safety = compute_broker_safety_state(broker_health)
        universe_state = await self._universe_resolver.resolve(session)
        kline_status = self._kline_service.get_status()
        broker_mode = settings.broker_mode.lower()
        mock_enabled = broker_mode != "moomoo"
        signal_provider = "MoomooMomentumResearchProvider" if broker_mode == "moomoo" else "LocalMomentumResearchProvider"
        signal_data_source = "moomoo_snapshot_plus_yfinance_kline" if broker_mode == "moomoo" else "local_generated"
        return RuntimeState(
            broker_mode=safety["broker_mode"],
            read_only=safety["read_only"],
            broker_adapter=type(self._broker).__name__,
            account_environment=safety["account_environment"],
            trading_universe=universe_state.symbols,
            trading_universe_source=universe_state.source,
            kline_provider=kline_status["provider"],
            kline_cache_enabled=bool(kline_status["cache_enabled"]),
            signal_data_source=signal_data_source,
            mock_enabled=mock_enabled,
            price_source_priority=["moomoo_quote_last_price", "moomoo_position_current_price", "yfinance_cached_latest_close", "DATA_ERROR"],
            signal_provider=signal_provider,
        )
