"""
Moomoo / Futu OpenAPI broker adapter — SAFE SKELETON ONLY.

This adapter is a placeholder for real moomoo OpenD integration.
It fails closed and never places real orders unless:
  - TRADING_ENABLED=true in settings
  - broker_mode is EXACTLY "moomoo"
  - all risk checks pass

TODOs for real integration:
  1. Install futu-api-sdk or moomoo-api-sdk (https://github.com/FutunnOpen/futu-api-sdk)
  2. Implement unlock_trade_password() flow (required for live trading)
  3. Map market codes: US market = "US" or 1 depending on SDK version
  4. Map US symbol format: some SDK versions require "US.AAPL" format
  5. Map order status: FillStatus -> OrderDto.status
  6. Implement callback handlers for order status updates
  7. Implement reconnect logic with exponential backoff
  8. Handle paper vs real trading environment in OpenD config

Usage example (when SDK is available):
    from futu import OpenSecTradeContext, TradeDealSide, TrdEnv
    ctx = OpenSecTradeContext(TrdEnv.SIMULATE, host=settings.opend_host, port=settings.opend_port)
    # ... see futu SDK docs: https://futunnopen.github.io/futu-api-doc/
"""
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.services.broker.base import (
    BrokerAdapter,
    AccountSummary,
    PositionDto,
    OrderDto,
    QuoteDto,
    LimitOrderRequest,
    BrokerHealth,
)

logger = logging.getLogger(__name__)

# Try to import moomoo SDK; fail gracefully if not available
try:
    from futu import OpenSecTradeContext, TrdEnv, TrdSide, OrderOp, OpenFutureContext
    MOOMOO_SDK_AVAILABLE = True
except ImportError:
    MOOMOO_SDK_AVAILABLE = False
    logger.warning("Moomoo/Futu SDK not installed. MoomooBrokerAdapter will be unavailable.")


class MoomooBrokerAdapter:
    def __init__(self) -> None:
        self._connected = False
        self._ctx = None

    async def connect(self) -> None:
        if not MOOMOO_SDK_AVAILABLE:
            logger.error("Cannot connect: Moomoo SDK not installed")
            self._connected = False
            return
        if not settings.trading_enabled:
            logger.info("Moomoo: skipping connect (trading_enabled=false)")
            self._connected = True
            return
        # TODO: implement real connection
        #   ctx = OpenSecTradeContext(
        #       TrdEnv.SIMULATE if not settings.trading_enabled else TrdEnv.REAL,
        #       host=settings.opend_host,
        #       port=settings.opend_port,
        #   )
        #   ctx.start()
        logger.warning("Moomoo connect: not yet implemented (safe skeleton)")
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        if self._ctx:
            pass  # self._ctx.close()

    async def health_check(self) -> BrokerHealth:
        if not MOOMOO_SDK_AVAILABLE:
            return BrokerHealth(connected=False, latency_ms=None, message="SDK not installed")
        # TODO: ping OpenD to verify connection
        return BrokerHealth(
            connected=self._connected,
            latency_ms=None,
            message="Moomoo adapter skeleton (not yet connected to OpenD)" if not self._connected else "Connected",
        )

    async def get_account(self) -> AccountSummary:
        # TODO: implement
        #   ret, acc = self._ctx.get_acc_list()
        #   ret, info = self._ctx.accinfo_query(acc[0])
        logger.warning("Moomoo get_account: using mock fallback")
        return AccountSummary(
            total_value=0.0, cash=0.0, positions_value=0.0,
            day_pnl=0.0, day_pnl_pct=0.0, total_pnl=0.0, total_pnl_pct=0.0,
            drawdown_pct=0.0, buying_power=0.0, currency="USD",
        )

    async def get_positions(self) -> list[PositionDto]:
        # TODO: implement using ctx.position_list_query()
        logger.warning("Moomoo get_positions: using mock fallback")
        return []

    async def get_open_orders(self) -> list[OrderDto]:
        # TODO: implement using ctx.order_list_query()
        return []

    async def get_quote(self, symbol: str) -> QuoteDto:
        # TODO: implement using OpenFutureContext or quote methods
        #   ret, data = quote_ctx.get_stock_quote(["US." + symbol])
        logger.warning("Moomoo get_quote: using mock fallback")
        return QuoteDto(symbol=symbol, bid=None, ask=None, last=None, volume=None,
                        bid_size=None, ask_size=None, timestamp=datetime.now(timezone.utc))

    async def place_limit_order(self, request: LimitOrderRequest) -> OrderDto:
        """Place a limit order via moomoo OpenD.

        Safety: this will ONLY place real orders if:
          - MOOMOO_SDK_AVAILABLE is True
          - settings.trading_enabled is True
          - settings.broker_mode is 'moomoo'
        Otherwise it returns a rejected order.
        """
        if not MOOMOO_SDK_AVAILABLE:
            raise RuntimeError("Moomoo SDK not installed")
        if not settings.trading_enabled:
            raise RuntimeError("Trading is disabled")
        if settings.broker_mode != "moomoo":
            raise RuntimeError("Broker mode is not moomoo")

        # TODO: implement real order placement
        #   ret, data = self._ctx.place_order(
        #       price=request.limit_price,
        #       qty=request.quantity,
        #       code="US." + request.symbol,
        #       trd_side=TrdSide.BUY if request.side.upper() == "BUY" else TrdSide.SELL,
        #       order_type=OrderOp.NORMAL,
        #       trd_env=TrdEnv.SIMULATE,
        #   )
        #   # map response to OrderDto
        logger.error("Moomoo place_limit_order: not implemented (safe skeleton)")
        raise NotImplementedError("Moomoo place_order not implemented in this version")

    async def cancel_order(self, order_id: str) -> None:
        # TODO: implement using ctx.modify_order()
        logger.warning("Moomoo cancel_order: not implemented (safe skeleton)")
        raise NotImplementedError("Moomoo cancel_order not implemented in this version")
