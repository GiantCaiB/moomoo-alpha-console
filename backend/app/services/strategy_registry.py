"""Strategy Registry — metadata-only mapping of strategy types to definitions.

This registry holds static metadata (version, description, default parameters,
rules summary) for each known strategy key. It does NOT hold factory functions
or class references — the actual runner logic lives in the existing strategy
and service modules.

New profiles can be added by registering a new StrategyDef. The DB
strategy_profiles table mirrors this metadata for persistence and user config.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StrategyDef:
    version: str
    description: str
    default_parameters: dict[str, Any]
    rules_summary: dict[str, Any]
    display_name: str = ""


_ENTRY_PARAMS: dict[str, Any] = {
    "buy_score_threshold": 75,
    "watch_score_threshold": 65,
    "weights": {
        "trend": 25,
        "relative_strength": 20,
        "volume": 10,
        "entry_quality": 15,
        "risk_reward": 15,
        "market_regime": 15,
    },
    "benchmark": "SPY",
    "min_bars": 220,
    "relative_strength_filters": {
        "underperform_spy_20d_hard_fail_margin_pct": 3,
        "underperform_spy_60d_hard_fail_margin_pct": 5,
    },
}

_ENTRY_RULES: dict[str, Any] = {
    "type": "entry",
    "scoring_weights": _ENTRY_PARAMS["weights"],
    "thresholds": {
        "buy": _ENTRY_PARAMS["buy_score_threshold"],
        "watch": _ENTRY_PARAMS["watch_score_threshold"],
    },
    "benchmark": _ENTRY_PARAMS["benchmark"],
    "min_bars": _ENTRY_PARAMS["min_bars"],
    "relative_strength_filters": {
        "hard_fail_margins": {
            "20d": _ENTRY_PARAMS["relative_strength_filters"]["underperform_spy_20d_hard_fail_margin_pct"],
            "60d": _ENTRY_PARAMS["relative_strength_filters"]["underperform_spy_60d_hard_fail_margin_pct"],
        },
        "description": "Underperformance beyond these margins triggers AVOID. Minor underperformance within margins may downgrade BUY to WATCH.",
    },
}

_POSITION_PARAMS: dict[str, Any] = {
    "trim_thresholds": [
        {"gain_pct": 25, "trim_pct": 10},
        {"gain_pct": 50, "trim_pct": 15},
        {"gain_pct": 75, "trim_pct": 20},
    ],
    "tail_threshold_pct": 100,
    "loss_defense": {
        "review_pct": -8,
        "stop_adding_pct": -15,
        "reduce_risk_pct": -20,
        "exit_review_pct": -30,
    },
    "tail_exit": {
        "weekly_sma_trim": 20,
        "weekly_sma_exit": 30,
        "drawdown_exit_pct": 35,
    },
}

_POSITION_RULES: dict[str, Any] = {
    "type": "position_guidance",
    "trim_thresholds": _POSITION_PARAMS["trim_thresholds"],
    "tail_threshold_pct": _POSITION_PARAMS["tail_threshold_pct"],
    "loss_defense": _POSITION_PARAMS["loss_defense"],
    "tail_exit": _POSITION_PARAMS["tail_exit"],
}


class StrategyRegistry:
    _defs: dict[tuple[str, str], StrategyDef] = {}

    @classmethod
    def register(
        cls,
        strategy_type: str,
        strategy_key: str,
        definition: StrategyDef,
    ) -> None:
        cls._defs[(strategy_type, strategy_key)] = definition

    @classmethod
    def get(cls, strategy_type: str, strategy_key: str) -> StrategyDef | None:
        return cls._defs.get((strategy_type, strategy_key))

    @classmethod
    def list_by_type(cls, strategy_type: str) -> list[tuple[str, StrategyDef]]:
        return [
            (key, defn)
            for (st, key), defn in cls._defs.items()
            if st == strategy_type
        ]

    @classmethod
    def get_default_parameters(cls, strategy_type: str, strategy_key: str) -> dict[str, Any] | None:
        defn = cls.get(strategy_type, strategy_key)
        if defn is None:
            return None
        return copy.deepcopy(defn.default_parameters)

    @classmethod
    def get_rules_summary(cls, strategy_type: str, strategy_key: str) -> dict[str, Any] | None:
        defn = cls.get(strategy_type, strategy_key)
        if defn is None:
            return None
        return copy.deepcopy(defn.rules_summary)

    @classmethod
    def merge_parameters(
        cls,
        strategy_type: str,
        strategy_key: str,
        overrides: dict[str, Any] | None,
    ) -> dict[str, Any]:
        defaults = cls.get_default_parameters(strategy_type, strategy_key) or {}
        if overrides:
            merged = copy.deepcopy(defaults)
            merged.update(overrides)
            return merged
        return defaults


StrategyRegistry.register(
    "entry",
    "momentum_relative_strength",
    StrategyDef(
        version="1.0.0",
        description="Momentum and relative strength screener for new position ideas.",
        default_parameters=_ENTRY_PARAMS,
        rules_summary=_ENTRY_RULES,
        display_name="Momentum Relative Strength v1",
    ),
)

StrategyRegistry.register(
    "position_guidance",
    "profit_tail_loss_defense",
    StrategyDef(
        version="1.0.0",
        description="Combined profit tail management for winners and loss defense for deteriorating positions.",
        default_parameters=_POSITION_PARAMS,
        rules_summary=_POSITION_RULES,
        display_name="Profit Tail + Loss Defense v1",
    ),
)
