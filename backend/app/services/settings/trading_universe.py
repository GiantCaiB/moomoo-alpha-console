import json
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.app_setting import AppSetting
from app.services.kline.symbol_map import normalize_symbol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradingUniverseState:
    symbols: list[str]
    source: str


class TradingUniverseResolver:
    @staticmethod
    def get_default_symbols() -> list[str]:
        return list(settings.universe_symbols or [])

    @staticmethod
    def normalize_symbols(symbols: list[str]) -> tuple[list[str], list[str]]:
        cleaned: list[str] = []
        invalid: list[str] = []
        seen: set[str] = set()
        for raw in symbols:
            normalized = normalize_symbol(raw)
            if not normalized:
                invalid.append(str(raw))
                continue
            if normalized not in seen:
                seen.add(normalized)
                cleaned.append(normalized)
        return cleaned, invalid

    async def resolve(self, session: AsyncSession) -> TradingUniverseState:
        default_symbols = self.get_default_symbols()
        result = await session.execute(
            select(AppSetting).where(AppSetting.key == "trading_universe")
        )
        row = result.scalar_one_or_none()

        if row is not None and row.value:
            if row.description is None or "User-defined trading universe" in row.description:
                parsed = self._parse_symbols(row.value)
                if parsed:
                    symbols, _ = self.normalize_symbols(parsed)
                    if symbols:
                        return TradingUniverseState(symbols=symbols, source="database")

        if default_symbols:
            symbols, _ = self.normalize_symbols(default_symbols)
            return TradingUniverseState(symbols=symbols, source="default")

        if row is not None and row.value:
            parsed = self._parse_symbols(row.value)
            if parsed:
                symbols, _ = self.normalize_symbols(parsed)
                if symbols:
                    return TradingUniverseState(symbols=symbols, source="database")

        return TradingUniverseState(symbols=[], source="default")

    def validate_symbols(self, symbols: list[str]) -> list[str]:
        cleaned, invalid = self.normalize_symbols(symbols)
        if invalid:
            raise ValueError(f"Invalid trading universe symbols: {', '.join(invalid)}")
        if not cleaned:
            raise ValueError("Trading universe cannot be empty")
        return cleaned

    @staticmethod
    def _parse_symbols(value: str) -> list[str]:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            logger.warning("Failed to parse trading_universe value from database")
            return []
        if not isinstance(parsed, list):
            return []
        return [str(symbol).strip().upper() for symbol in parsed if str(symbol).strip()]
