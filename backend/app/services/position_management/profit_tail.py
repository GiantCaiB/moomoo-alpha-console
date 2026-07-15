import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position_lifecycle_state import PositionLifecycleState
from app.models.position_management_signal import PositionManagementSignal
from app.models.position_guidance_run import PositionGuidanceRun
import json
from app.services.broker.base import BrokerAdapter
from app.services.kline.service import KLineService
from app.services.market_data.price_resolver import PriceResolver

logger = logging.getLogger(__name__)


POSITION_SIGNAL_DATA_SOURCE = "moomoo_positions_plus_yfinance_kline"


@dataclass(frozen=True)
class ProfitTailSignalResult:
    symbol: str
    signal: str
    reason: str
    current_price: float | None
    avg_cost: float | None
    quantity: float | None
    gain_pct: float | None
    suggested_action: str | None
    suggested_quantity: float | None
    suggested_trim_pct: float | None
    tail_mode: bool
    weekly_close: float | None
    weekly_sma20: float | None
    weekly_sma30: float | None
    drawdown_from_high: float | None
    data_source: str
    price_source: str | None
    bar_source: str | None
    is_real_market_data: bool
    generated_at: datetime
    original_cost_basis: float | None = None
    highest_price_since_entry: float | None = None
    tail_started_at: datetime | None = None
    trim_25_done: bool | None = None
    trim_50_done: bool | None = None
    trim_75_done: bool | None = None
    strategy_profile_id: str | None = None
    strategy_version: str | None = None
    parameters_snapshot_json: str | None = None
    run_id: str | None = None


@dataclass
class ProfitTailEvalState:
    highest_price_since_entry: float
    tail_mode: bool
    original_cost_basis: float | None
    tail_started_at: datetime | None
    trim_25_done: bool
    trim_50_done: bool
    trim_75_done: bool


@dataclass
class PositionLifecycleSnapshot:
    state: PositionLifecycleState
    eval_state: ProfitTailEvalState
    was_created: bool


class ProfitTailStrategyService:
    def __init__(
        self,
        broker: BrokerAdapter,
        kline_service: KLineService,
        price_resolver: PriceResolver,
        strategy_profile_id: str | None = None,
        strategy_version: str | None = None,
        parameters: dict | None = None,
    ) -> None:
        self._broker = broker
        self._kline = kline_service
        self._price_resolver = price_resolver
        self._strategy_profile_id = strategy_profile_id
        self._strategy_version = strategy_version
        self._parameters = parameters or {}

    @property
    def _trim_thresholds(self) -> list[dict]:
        return self._parameters.get("trim_thresholds", [
            {"gain_pct": 25, "trim_pct": 10},
            {"gain_pct": 50, "trim_pct": 15},
            {"gain_pct": 75, "trim_pct": 20},
        ])

    @property
    def _tail_threshold_pct(self) -> float:
        return float(self._parameters.get("tail_threshold_pct", 100))

    @property
    def _loss_defense(self) -> dict:
        return self._parameters.get("loss_defense", {
            "review_pct": -8,
            "stop_adding_pct": -15,
            "reduce_risk_pct": -20,
            "exit_review_pct": -30,
        })

    @property
    def _tail_exit(self) -> dict:
        return self._parameters.get("tail_exit", {
            "weekly_sma_trim": 20,
            "weekly_sma_exit": 30,
            "drawdown_exit_pct": 35,
        })

    def _make_parameters_snapshot(self) -> str | None:
        if self._parameters:
            return json.dumps(self._parameters)
        return None

    async def run(self, session: AsyncSession, run: PositionGuidanceRun | None = None) -> tuple[list[ProfitTailSignalResult], dict]:
        if run is None:
            run = PositionGuidanceRun(
                strategy_profile_id=self._strategy_profile_id,
                strategy_name="profit_tail_loss_defense",
                strategy_version=self._strategy_version,
                status="RUNNING",
                started_at=datetime.now(timezone.utc),
                parameters_snapshot_json=self._make_parameters_snapshot() or json.dumps({}),
            )
            session.add(run)
            await session.flush()
        try:
            positions = await self._broker.get_positions()
            active_positions = [position for position in positions if (position.quantity or 0) > 0]
        except Exception as exc:
            run.status = "FAILED"
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
            raise

        results: list[ProfitTailSignalResult] = []
        data_error_count = 0

        for position in active_positions:
            try:
                snapshot = await self._load_or_create_state(session, position.symbol, position.quantity, position.avg_cost)
                signal = await self._evaluate_position(session, position, snapshot.eval_state)
                results.append(signal)
                if signal.signal == "DATA_ERROR":
                    data_error_count += 1
                snapshot.state.highest_price_since_entry = snapshot.eval_state.highest_price_since_entry
                await self._persist_signal(session, signal, snapshot.state, run.id)
            except Exception as exc:
                logger.exception("Position guidance error for %s: %s", position.symbol, exc)
                error_signal = self._data_error(
                    symbol=position.symbol,
                    avg_cost=position.avg_cost,
                    quantity=float(position.quantity or 0),
                    reason=f"Evaluation failed: {exc}",
                    bar_source="yfinance_cached_daily_bars",
                )
                results.append(error_signal)
                data_error_count += 1
                try:
                    res = await self._load_or_create_state(session, position.symbol, position.quantity, position.avg_cost)
                    await self._persist_signal(session, error_signal, res.state, run.id)
                except Exception as persist_exc:
                    logger.warning("Could not persist DATA_ERROR signal for %s: %s", position.symbol, persist_exc)

        await session.commit()
        run.positions_scanned = len(active_positions)
        run.signals_generated = len(results)
        run.data_error_count = data_error_count
        run.status = "COMPLETED"
        run.finished_at = datetime.now(timezone.utc)
        await session.commit()
        summary = {
            "id": run.id,
            "strategy_profile_id": run.strategy_profile_id,
            "strategy_name": run.strategy_name,
            "strategy_version": run.strategy_version,
            "status": "COMPLETED",
            "positions_scanned": len(active_positions),
            "signals_generated": len(results),
            "data_error_count": data_error_count,
            "read_only": True,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "parameters_snapshot_json": run.parameters_snapshot_json,
        }
        return results, summary

    async def list_signals(self, session: AsyncSession, include_history: bool = False, active_symbols: set[str] | None = None) -> list[ProfitTailSignalResult]:
        query = select(PositionManagementSignal).order_by(PositionManagementSignal.generated_at.desc(), PositionManagementSignal.created_at.desc())
        result = await session.execute(query)
        rows = result.scalars().all()
        if not include_history:
            seen: set[str] = set()
            filtered = []
            for row in rows:
                if row.symbol in seen:
                    continue
                seen.add(row.symbol)
                filtered.append(row)
            rows = filtered
        if active_symbols is not None:
            rows = [row for row in rows if row.symbol in active_symbols]
        return [self._row_to_result(row) for row in rows]

    async def _load_or_create_state(self, session: AsyncSession, symbol: str, quantity: float, avg_cost: float) -> PositionLifecycleSnapshot:
        result = await session.execute(select(PositionLifecycleState).where(PositionLifecycleState.symbol == symbol))
        state = result.scalar_one_or_none()
        was_created = False
        current_price = None
        if state is None:
            state = PositionLifecycleState(
                symbol=symbol,
                original_entry_price=float(avg_cost or 0.0),
                original_quantity=float(quantity or 0),
                original_cost_basis=float((avg_cost or 0.0) * (quantity or 0)),
                highest_price_since_entry=0.0,
                trim_25_done=False,
                trim_50_done=False,
                trim_75_done=False,
                tail_mode=False,
                tail_started_at=None,
                tail_original_quantity=None,
                notes=None,
            )
            session.add(state)
            was_created = True
        eval_state = ProfitTailEvalState(
            highest_price_since_entry=state.highest_price_since_entry,
            tail_mode=state.tail_mode,
            original_cost_basis=state.original_cost_basis,
            tail_started_at=state.tail_started_at,
            trim_25_done=state.trim_25_done,
            trim_50_done=state.trim_50_done,
            trim_75_done=state.trim_75_done,
        )
        return PositionLifecycleSnapshot(state=state, eval_state=eval_state, was_created=was_created)

    async def _evaluate_position(self, session: AsyncSession, position, eval_state: ProfitTailEvalState) -> ProfitTailSignalResult:
        symbol = position.symbol
        quantity = float(position.quantity or 0)
        avg_cost = float(position.avg_cost) if position.avg_cost is not None else None

        if quantity <= 0:
            return self._data_error(symbol, avg_cost, quantity, "Zero quantity")
        if avg_cost is None or avg_cost <= 0:
            return self._data_error(symbol, avg_cost, quantity, "Missing avg_cost")

        kline_result = await self._kline.get_cached_or_fetch_daily_bars(symbol, lookback_days=400, session=session)
        bars = kline_result.bars
        daily_bars = self._normalize_daily_bars(bars)
        if daily_bars is None or daily_bars.empty:
            reason = kline_result.fetch_error or "Invalid K-line data"
            return self._data_error(symbol, avg_cost, quantity, reason, kline_result.latest_cached_close, bar_source="yfinance_cached_daily_bars")

        weekly_bars = self._resample_weekly_bars(daily_bars)
        if weekly_bars is None or len(weekly_bars) < 30:
            return self._data_error(symbol, avg_cost, quantity, "Insufficient weekly bars for SMA30", kline_result.latest_cached_close, bar_source="yfinance_cached_daily_bars")

        price_resolution = await self._price_resolver.resolve(symbol, bars=daily_bars, session=session)
        current_price = price_resolution.price
        if current_price is None or current_price <= 0:
            return self._data_error(symbol, avg_cost, quantity, price_resolution.error or "No current price available", kline_result.latest_cached_close, bar_source="yfinance_cached_daily_bars")

        highest = float(eval_state.highest_price_since_entry or 0.0)
        if highest <= 0:
            highest = current_price
        if current_price > highest:
            highest = current_price
            eval_state.highest_price_since_entry = highest

        gain_pct = ((current_price - avg_cost) / avg_cost) * 100.0
        drawdown_from_high = ((highest - current_price) / highest) * 100.0 if highest > 0 else None

        weekly_close = float(weekly_bars["close"].iloc[-1])
        weekly_sma20 = self._sma(weekly_bars, 20)
        weekly_sma30 = self._sma(weekly_bars, 30)
        daily_sma200 = self._sma(daily_bars, 200)

        ld = self._loss_defense
        tail_exit = self._tail_exit
        drawdown_exit_pct = float(tail_exit.get("drawdown_exit_pct", 35))
        sma_trim = int(tail_exit.get("weekly_sma_trim", 20))
        sma_exit = int(tail_exit.get("weekly_sma_exit", 30))

        signal = "HOLD"
        reason = "Gain below first trim threshold."
        suggested_action = "Hold position"
        suggested_quantity = None
        suggested_trim_pct = None

        if drawdown_from_high is not None and drawdown_from_high >= drawdown_exit_pct:
            signal = "EXIT_POSITION"
            reason = f"Position drawdown from high exceeded {drawdown_exit_pct:.0f}%; review exit manually."
            suggested_action = "Review exit manually"
            suggested_trim_pct = 100
            suggested_quantity = quantity
        elif gain_pct <= float(ld.get("exit_review_pct", -30)) or (daily_sma200 is not None and current_price < daily_sma200 and gain_pct <= float(ld.get("exit_review_pct", -30))):
            exit_pct = abs(ld.get("exit_review_pct", -30))
            signal = "EXIT_POSITION"
            reason = f"Position down more than {exit_pct:.0f}%; major risk threshold breached. Review exit manually."
            suggested_action = "Review exit manually"
            suggested_trim_pct = 100
            suggested_quantity = quantity
        elif gain_pct <= float(ld.get("reduce_risk_pct", -20)) or (daily_sma200 is not None and current_price < daily_sma200 and gain_pct <= float(ld.get("reduce_risk_pct", -20))):
            reduce_pct = abs(ld.get("reduce_risk_pct", -20))
            signal = "REDUCE_RISK"
            reason = f"Position down more than {reduce_pct:.0f}%; consider reducing exposure manually."
            suggested_action = "Reduce exposure manually"
            suggested_trim_pct = 50
            suggested_quantity = round(quantity / 2, 6)
        elif gain_pct <= float(ld.get("stop_adding_pct", -15)) or (daily_sma200 is not None and current_price < daily_sma200 and gain_pct <= float(ld.get("stop_adding_pct", -15))):
            stop_pct = abs(ld.get("stop_adding_pct", -15))
            signal = "STOP_ADDING"
            reason = f"Position down more than {stop_pct:.0f}%; do not add until thesis and trend improve."
            suggested_action = "Do not add until thesis and trend improve"
        elif gain_pct <= float(ld.get("review_pct", -8)):
            review_pct = abs(ld.get("review_pct", -8))
            signal = "REVIEW_POSITION"
            reason = f"Position down more than {review_pct:.0f}%; review thesis and risk."
            suggested_action = "Review thesis and risk manually"
        elif eval_state.tail_mode and gain_pct >= 0:
            if drawdown_from_high is not None and drawdown_from_high >= drawdown_exit_pct:
                signal = "EXIT_TAIL"
                reason = "Tail trend broken or drawdown exceeded limit."
                suggested_action = "Exit tail manually"
                suggested_trim_pct = 100
                suggested_quantity = quantity
            elif weekly_sma30 is not None and weekly_close < weekly_sma30:
                signal = "EXIT_TAIL"
                reason = "Tail trend broken or drawdown exceeded limit."
                suggested_action = "Exit tail manually"
                suggested_trim_pct = 100
                suggested_quantity = quantity
            elif weekly_sma20 is not None and weekly_close < weekly_sma20:
                signal = "TRIM_TAIL"
                reason = "Tail position lost weekly SMA20 but remains above weekly SMA30."
                suggested_action = "Trim tail position"
                suggested_trim_pct = 50
                suggested_quantity = round(quantity / 2, 6)
            else:
                signal = "HOLD_TAIL"
                reason = "Tail position remains above weekly SMA20."
                suggested_action = "Hold tail position"
        else:
            tail_threshold = self._tail_threshold_pct
            if gain_pct >= tail_threshold:
                signal = "ENTER_TAIL_MODE"
                reason = f"Position is up {tail_threshold:.0f}%+. Consider recovering original cost basis and keeping remaining shares as a profit tail."
                suggested_action = "Recover cost basis and keep remaining shares as profit tail"
                shares_to_recover_cost = (eval_state.original_cost_basis or (avg_cost * quantity)) / current_price if current_price > 0 else quantity * 0.5
                candidate = min(quantity * 0.5, shares_to_recover_cost)
                suggested_quantity = round(candidate, 6) if candidate and candidate > 0 else round(quantity * 0.5, 6)
            else:
                trim_found = False
                for trim_def in sorted(self._trim_thresholds, key=lambda t: t["gain_pct"], reverse=True):
                    tg = float(trim_def["gain_pct"])
                    tp = float(trim_def["trim_pct"])
                    trim_flag = f"trim_{int(tg)}_done"
                    trim_attr = getattr(eval_state, trim_flag, None)
                    if gain_pct >= tg and not trim_attr:
                        signal = "TRIM_PROFIT"
                        reason = f"Position is up {tg:.0f}%+, trim level not completed."
                        suggested_action = f"Trim {tp:.0f}% of position"
                        suggested_trim_pct = tp
                        suggested_quantity = round(quantity * (tp / 100.0), 6)
                        trim_found = True
                        break
                if not trim_found:
                    signal = "HOLD"
                    reason = "Gain below first trim threshold."
                    suggested_action = "Hold position"

        return ProfitTailSignalResult(
            symbol=symbol,
            signal=signal,
            reason=reason,
            current_price=current_price,
            avg_cost=avg_cost,
            quantity=quantity,
            gain_pct=round(gain_pct, 2),
            suggested_action=suggested_action,
            suggested_quantity=suggested_quantity,
            suggested_trim_pct=suggested_trim_pct,
            tail_mode=bool(eval_state.tail_mode),
            weekly_close=round(weekly_close, 4),
            weekly_sma20=round(weekly_sma20, 4) if weekly_sma20 is not None else None,
            weekly_sma30=round(weekly_sma30, 4) if weekly_sma30 is not None else None,
            drawdown_from_high=round(drawdown_from_high, 2) if drawdown_from_high is not None else None,
            data_source=POSITION_SIGNAL_DATA_SOURCE,
            price_source=price_resolution.price_source,
            bar_source="yfinance_cached_daily_bars",
            is_real_market_data=True,
            generated_at=datetime.now(timezone.utc),
            original_cost_basis=eval_state.original_cost_basis,
            highest_price_since_entry=eval_state.highest_price_since_entry,
            tail_started_at=eval_state.tail_started_at,
            trim_25_done=eval_state.trim_25_done,
            trim_50_done=eval_state.trim_50_done,
            trim_75_done=eval_state.trim_75_done,
            strategy_profile_id=self._strategy_profile_id,
            strategy_version=self._strategy_version,
            parameters_snapshot_json=self._make_parameters_snapshot(),
        )

    async def _persist_signal(self, session: AsyncSession, signal: ProfitTailSignalResult, state: PositionLifecycleState, run_id: str) -> None:
        session.add(
            PositionManagementSignal(
                run_id=run_id,
                symbol=signal.symbol,
                signal=signal.signal,
                reason=signal.reason,
                current_price=signal.current_price,
                avg_cost=signal.avg_cost,
                quantity=signal.quantity,
                gain_pct=signal.gain_pct,
                suggested_action=signal.suggested_action,
                suggested_quantity=signal.suggested_quantity,
                suggested_trim_pct=signal.suggested_trim_pct,
                tail_mode=signal.tail_mode,
                weekly_close=signal.weekly_close,
                weekly_sma20=signal.weekly_sma20,
                weekly_sma30=signal.weekly_sma30,
                drawdown_from_high=signal.drawdown_from_high,
                original_cost_basis=signal.original_cost_basis,
                highest_price_since_entry=signal.highest_price_since_entry,
                data_source=signal.data_source,
                price_source=signal.price_source,
                bar_source=signal.bar_source,
                is_real_market_data=signal.is_real_market_data,
                generated_at=signal.generated_at,
                strategy_profile_id=signal.strategy_profile_id,
                strategy_version=signal.strategy_version,
                parameters_snapshot_json=signal.parameters_snapshot_json,
            )
        )
        if signal.current_price is not None and signal.current_price > (state.highest_price_since_entry or 0):
            state.highest_price_since_entry = signal.current_price

    def _data_error(
        self,
        symbol: str,
        avg_cost: float | None,
        quantity: float,
        reason: str,
        current_price: float | None = None,
        *,
        bar_source: str | None = None,
    ) -> ProfitTailSignalResult:
        return ProfitTailSignalResult(
            symbol=symbol,
            signal="DATA_ERROR",
            reason=reason,
            current_price=current_price,
            avg_cost=avg_cost,
            quantity=quantity,
            gain_pct=None,
            suggested_action=None,
            suggested_quantity=None,
            suggested_trim_pct=None,
            tail_mode=False,
            weekly_close=None,
            weekly_sma20=None,
            weekly_sma30=None,
            drawdown_from_high=None,
            data_source=POSITION_SIGNAL_DATA_SOURCE,
            price_source="DATA_ERROR" if current_price is None else "yfinance_cached_latest_close",
            bar_source=bar_source or "yfinance_cached_daily_bars",
            is_real_market_data=True,
            generated_at=datetime.now(timezone.utc),
            strategy_profile_id=self._strategy_profile_id,
            strategy_version=self._strategy_version,
            parameters_snapshot_json=self._make_parameters_snapshot(),
        )

    @staticmethod
    def _normalize_daily_bars(df: pd.DataFrame) -> pd.DataFrame | None:
        if df is None or df.empty:
            return None
        bars = df.copy()
        date_column = "date" if "date" in bars.columns else "bar_date" if "bar_date" in bars.columns else None
        if date_column is None:
            return None
        bars[date_column] = pd.to_datetime(bars[date_column], errors="coerce")
        bars = bars.dropna(subset=[date_column, "close"])
        if bars.empty:
            return None
        bars = bars.rename(columns={date_column: "date"}).sort_values("date")
        return bars

    @staticmethod
    def _resample_weekly_bars(daily_bars: pd.DataFrame) -> pd.DataFrame | None:
        if daily_bars is None or daily_bars.empty:
            return None
        bars = daily_bars.copy()
        bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
        bars = bars.dropna(subset=["date", "close"]).sort_values("date")
        if bars.empty:
            return None
        weekly = (
            bars.set_index("date")
            .resample("W-FRI")
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                    "adj_close": "last" if "adj_close" in bars.columns else "last",
                }
            )
            .dropna(subset=["close"])
            .reset_index()
        )
        return weekly if not weekly.empty else None

    @staticmethod
    def _sma(bars: pd.DataFrame, period: int) -> float | None:
        if len(bars) < period:
            return None
        return float(bars["close"].tail(period).mean())

    @staticmethod
    def _row_to_result(row: PositionManagementSignal) -> ProfitTailSignalResult:
        return ProfitTailSignalResult(
            symbol=row.symbol,
            signal=row.signal,
            reason=row.reason or "",
            current_price=row.current_price,
            avg_cost=row.avg_cost,
            quantity=row.quantity,
            gain_pct=row.gain_pct,
            suggested_action=row.suggested_action,
            suggested_quantity=row.suggested_quantity,
            suggested_trim_pct=row.suggested_trim_pct,
            tail_mode=row.tail_mode,
            weekly_close=row.weekly_close,
            weekly_sma20=row.weekly_sma20,
            weekly_sma30=row.weekly_sma30,
            drawdown_from_high=row.drawdown_from_high,
            data_source=row.data_source or POSITION_SIGNAL_DATA_SOURCE,
            price_source=row.price_source,
            bar_source=row.bar_source,
            is_real_market_data=row.is_real_market_data,
            generated_at=row.generated_at,
            original_cost_basis=row.original_cost_basis,
            highest_price_since_entry=row.highest_price_since_entry,
            tail_started_at=None,
            trim_25_done=None,
            trim_50_done=None,
            trim_75_done=None,
            strategy_profile_id=row.strategy_profile_id,
            strategy_version=row.strategy_version,
            parameters_snapshot_json=row.parameters_snapshot_json,
            run_id=row.run_id,
        )
