import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_ENV_FILE, settings
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
    def read_env_file() -> str:
        try:
            return BACKEND_ENV_FILE.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    @classmethod
    def get_env_symbols(cls) -> list[str]:
        return cls.get_default_symbols()

    @classmethod
    def get_file_env_symbols(cls) -> list[str]:
        content = cls.read_env_file()
        match = re.search(r"(?m)^\s*UNIVERSE_SYMBOLS\s*=\s*(.*?)\s*$", content)
        if not match:
            return []
        value = match.group(1).strip().strip('"').strip("'")
        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(symbol).strip().upper() for symbol in parsed if str(symbol).strip()]
            except json.JSONDecodeError:
                return []
        return [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]

    @classmethod
    def write_env_symbols(cls, symbols: list[str]) -> str:
        old_content = cls.read_env_file()
        line = f"UNIVERSE_SYMBOLS={json.dumps(symbols, separators=(',', ':'))}"
        if re.search(r"(?m)^\s*UNIVERSE_SYMBOLS\s*=.*$", old_content):
            new_content = re.sub(
                r"(?m)^\s*UNIVERSE_SYMBOLS\s*=.*$",
                line,
                old_content,
                count=1,
            )
        else:
            new_content = old_content + ("\n" if old_content and not old_content.endswith("\n") else "") + line + "\n"

        BACKEND_ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".env.", dir=BACKEND_ENV_FILE.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as temp_file:
                temp_file.write(new_content)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_name, BACKEND_ENV_FILE)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise
        settings.universe_symbols = list(symbols)
        return old_content

    @staticmethod
    def restore_env_file(content: str) -> None:
        BACKEND_ENV_FILE.write_text(content, encoding="utf-8")

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
        env_symbols = self.get_env_symbols()
        result = await session.execute(
            select(AppSetting).where(AppSetting.key == "trading_universe")
        )
        row = result.scalar_one_or_none()

        if env_symbols:
            symbols, _ = self.normalize_symbols(env_symbols)
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
