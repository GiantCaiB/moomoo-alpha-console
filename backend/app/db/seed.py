"""Seed built-in strategy profiles."""
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy_profile import StrategyProfile

logger = logging.getLogger(__name__)

ENTRY_PARAMS = {
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
}

ENTRY_RULES_SUMMARY = {
    "type": "entry",
    "scoring_weights": ENTRY_PARAMS["weights"],
    "thresholds": {
        "buy": ENTRY_PARAMS["buy_score_threshold"],
        "watch": ENTRY_PARAMS["watch_score_threshold"],
    },
    "benchmark": ENTRY_PARAMS["benchmark"],
    "min_bars": ENTRY_PARAMS["min_bars"],
    "verdicts": {
        "BUY_STARTER": f"Score >= {ENTRY_PARAMS['buy_score_threshold']} and all hard filters pass",
        "WATCH": f"Score >= {ENTRY_PARAMS['watch_score_threshold']} and all hard filters pass",
        "AVOID": f"Score < {ENTRY_PARAMS['watch_score_threshold']} or hard filter failure",
        "DATA_ERROR": "Missing or invalid data",
    },
}

POSITION_PARAMS = {
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

POSITION_RULES_SUMMARY = {
    "type": "position_guidance",
    "trim_thresholds": POSITION_PARAMS["trim_thresholds"],
    "tail_threshold_pct": POSITION_PARAMS["tail_threshold_pct"],
    "loss_defense": POSITION_PARAMS["loss_defense"],
    "tail_exit": POSITION_PARAMS["tail_exit"],
    "signal_explanation": {
        "HOLD": "Gain below first trim threshold or loss above review threshold.",
        "TRIM_PROFIT": "Gain threshold met; suggested trim percentage shown.",
        "ENTER_TAIL_MODE": f"Gain >= {POSITION_PARAMS['tail_threshold_pct']}%; consider recovering cost basis.",
        "HOLD_TAIL": "Tail mode active; weekly close above SMA20.",
        "TRIM_TAIL": "Tail mode active; weekly close below SMA20 but above SMA30.",
        "EXIT_TAIL": "Tail mode active; weekly close below SMA30 or drawdown >= 35%.",
        "REVIEW_POSITION": f"Loss >= {abs(POSITION_PARAMS['loss_defense']['review_pct'])}%; review thesis.",
        "STOP_ADDING": f"Loss >= {abs(POSITION_PARAMS['loss_defense']['stop_adding_pct'])}%; do not add.",
        "REDUCE_RISK": f"Loss >= {abs(POSITION_PARAMS['loss_defense']['reduce_risk_pct'])}%; reduce exposure.",
        "EXIT_POSITION": f"Loss >= {abs(POSITION_PARAMS['loss_defense']['exit_review_pct'])}% or drawdown >= 35%; exit review.",
        "DATA_ERROR": "Missing or invalid data.",
    },
}

BUILT_IN_PROFILES = [
    {
        "name": "Momentum Relative Strength v1",
        "strategy_type": "entry",
        "strategy_key": "momentum_relative_strength",
        "version": "1.0.0",
        "description": "Momentum and relative strength screener for new position ideas. Scores symbols on trend, relative strength, volume, entry quality, risk/reward, and market regime.",
        "parameters_json": ENTRY_PARAMS,
        "rules_summary_json": ENTRY_RULES_SUMMARY,
        "is_default": True,
    },
    {
        "name": "Profit Tail + Loss Defense v1",
        "strategy_type": "position_guidance",
        "strategy_key": "profit_tail_loss_defense",
        "version": "1.0.0",
        "description": "Combined profit tail management for winners and loss defense for deteriorating positions. Read-only guidance for existing holdings.",
        "parameters_json": POSITION_PARAMS,
        "rules_summary_json": POSITION_RULES_SUMMARY,
        "is_default": True,
    },
]


async def seed_strategy_profiles(session: AsyncSession) -> None:
    for profile_data in BUILT_IN_PROFILES:
        result = await session.execute(
            select(StrategyProfile).where(
                StrategyProfile.strategy_key == profile_data["strategy_key"],
                StrategyProfile.strategy_type == profile_data["strategy_type"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            continue

        profile = StrategyProfile(
            name=profile_data["name"],
            strategy_type=profile_data["strategy_type"],
            strategy_key=profile_data["strategy_key"],
            version=profile_data["version"],
            description=profile_data["description"],
            parameters_json=json.dumps(profile_data["parameters_json"]),
            rules_summary_json=json.dumps(profile_data["rules_summary_json"]),
            is_default=profile_data["is_default"],
            is_active=True,
        )
        session.add(profile)
        logger.info("Seeded strategy profile: %s (%s)", profile_data["name"], profile_data["strategy_type"])

    await session.commit()
