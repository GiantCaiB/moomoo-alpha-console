"""
Deterministic risk engine.

Every order must pass ALL active rules before it can be placed.
Returns a structured RiskDecision that the UI displays to the user.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.core.config import settings
from app.services.broker.base import AccountSummary, QuoteDto

logger = logging.getLogger(__name__)


@dataclass
class RiskDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    max_allowed_quantity: int | None = None


@dataclass
class OrderCheckContext:
    symbol: str
    side: str
    order_type: str
    quantity: int
    limit_price: float
    stop_level: float | None
    portfolio: AccountSummary | None
    quote: QuoteDto | None
    positions: list[dict]
    open_orders: list[dict]
    daily_loss_pct: float
    drawdown_pct: float
    kill_switch_enabled: bool
    broker_connected: bool
    strategy_run_id: str | None

    @property
    def position_value(self) -> float:
        return abs(self.limit_price * self.quantity)


type RiskRule = Callable[[OrderCheckContext], RiskDecision | None]


class RiskEngine:
    def __init__(self) -> None:
        self._kill_switch = False
        self._rules: list[RiskRule] = [
            rule_kill_switch,
            rule_broker_disconnected,
            rule_stale_quote,
            rule_missing_stop_loss,
            rule_must_be_limit,
            rule_symbol_in_universe,
            rule_position_size_max,
            rule_risk_per_trade_max,
            rule_daily_loss,
            rule_drawdown,
            rule_duplicate_open_order,
        ]

    @property
    def kill_switch_enabled(self) -> bool:
        return self._kill_switch

    def set_kill_switch(self, enabled: bool) -> None:
        self._kill_switch = enabled
        logger.warning("Kill switch %s", "ENABLED" if enabled else "DISABLED")

    def evaluate(self, ctx: OrderCheckContext) -> RiskDecision:
        reasons: list[str] = []
        warnings: list[str] = []

        for rule in self._rules:
            result = rule(ctx)
            if result is not None:
                if not result.allowed:
                    reasons.extend(result.reasons)
                warnings.extend(result.warnings)

        allowed = len(reasons) == 0 and not self._kill_switch
        max_qty = self._compute_max_quantity(ctx)

        if not allowed:
            logger.info("Order blocked: %s on %s | reasons: %s", ctx.side, ctx.symbol, reasons)

        return RiskDecision(
            allowed=allowed,
            reasons=reasons,
            warnings=warnings,
            max_allowed_quantity=max_qty,
        )

    def _compute_max_quantity(self, ctx: OrderCheckContext) -> int | None:
        if ctx.portfolio is None or ctx.portfolio.total_value <= 0:
            return None
        pos_value_limit = ctx.portfolio.total_value * (settings.max_position_pct / 100.0)
        max_by_pos = int(pos_value_limit / ctx.limit_price) if ctx.limit_price > 0 else 0
        return max(max_by_pos, 0)


def rule_kill_switch(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.kill_switch_enabled:
        return RiskDecision(allowed=False, reasons=["Global kill switch is enabled"])
    return None


def rule_broker_disconnected(ctx: OrderCheckContext) -> RiskDecision | None:
    if not ctx.broker_connected:
        return RiskDecision(allowed=False, reasons=["Broker is disconnected"])
    return None


def rule_stale_quote(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.quote and ctx.quote.last is not None:
        age = (datetime.now(timezone.utc) - ctx.quote.timestamp).total_seconds()
        if age > settings.max_quote_age_seconds:
            return RiskDecision(
                allowed=False,
                reasons=[f"Quote is stale ({age:.0f}s > {settings.max_quote_age_seconds}s max)"],
            )
    return None


def rule_missing_stop_loss(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.side.upper() == "BUY" and (ctx.stop_level is None or ctx.stop_level <= 0):
        return RiskDecision(allowed=False, reasons=["Missing or invalid stop loss"])
    return None


def rule_must_be_limit(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.order_type.upper() not in [t.upper() for t in settings.allowed_order_types]:
        return RiskDecision(
            allowed=False,
            reasons=[f"Order type '{ctx.order_type}' not allowed. Only limit orders permitted"],
        )
    return None


def rule_symbol_in_universe(ctx: OrderCheckContext) -> RiskDecision | None:
    approved_universe = [s.upper() for s in settings.universe_symbols]
    if approved_universe and ctx.symbol.upper() not in approved_universe:
        return RiskDecision(
            allowed=False,
            reasons=[f"{ctx.symbol} is not in the approved trading universe"],
        )
    return None


def rule_position_size_max(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.portfolio and ctx.portfolio.total_value > 0:
        max_pos_value = ctx.portfolio.total_value * (settings.max_position_pct / 100.0)
        existing_pos_value = 0.0
        for pos in ctx.positions:
            if pos.get("symbol", "").upper() == ctx.symbol.upper():
                existing_pos_value = pos.get("current_price", 0) * pos.get("quantity", 0)
                break
        new_total = existing_pos_value + ctx.position_value
        if new_total > max_pos_value:
            return RiskDecision(
                allowed=False,
                reasons=[
                    f"Position size {ctx.position_value:.2f} + existing {existing_pos_value:.2f} "
                    f"exceeds max {max_pos_value:.2f} ({settings.max_position_pct}% of portfolio)"
                ],
            )
    return None


def rule_risk_per_trade_max(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.portfolio and ctx.portfolio.total_value > 0 and ctx.stop_level:
        risk_per_share = abs(ctx.limit_price - ctx.stop_level)
        total_risk = risk_per_share * ctx.quantity
        max_risk = ctx.portfolio.total_value * (settings.max_risk_per_trade_pct / 100.0)
        if total_risk > max_risk:
            return RiskDecision(
                allowed=False,
                reasons=[
                    f"Risk ${total_risk:.2f} exceeds max ${max_risk:.2f} "
                    f"({settings.max_risk_per_trade_pct}% of portfolio)"
                ],
            )
    return None


def rule_daily_loss(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.daily_loss_pct > settings.daily_loss_limit_pct:
        return RiskDecision(
            allowed=False,
            reasons=[
                f"Daily loss {ctx.daily_loss_pct:.2f}% exceeds limit "
                f"{settings.daily_loss_limit_pct}%"
            ],
        )
    return None


def rule_drawdown(ctx: OrderCheckContext) -> RiskDecision | None:
    if ctx.drawdown_pct > settings.max_drawdown_hard_pct:
        return RiskDecision(
            allowed=False,
            reasons=[
                f"Drawdown {ctx.drawdown_pct:.2f}% exceeds hard limit "
                f"{settings.max_drawdown_hard_pct}%"
            ],
        )
    if ctx.drawdown_pct > settings.max_drawdown_soft_pct:
        return RiskDecision(
            allowed=False,
            reasons=[
                f"Drawdown {ctx.drawdown_pct:.2f}% exceeds soft limit "
                f"{settings.max_drawdown_soft_pct}%"
            ],
        )
    return None


def rule_duplicate_open_order(ctx: OrderCheckContext) -> RiskDecision | None:
    for o in ctx.open_orders:
        if (o.get("symbol", "").upper() == ctx.symbol.upper()
                and o.get("side", "").upper() == ctx.side.upper()
                and o.get("status") in ("PENDING", "SUBMITTED")):
            return RiskDecision(
                allowed=False,
                reasons=[f"Duplicate open {ctx.side} order for {ctx.symbol} already exists"],
            )
    return None
