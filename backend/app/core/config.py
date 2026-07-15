import json
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, Literal


BACKEND_DIR = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Moomoo Alpha Console"
    debug: bool = True

    broker_mode: Literal["mock", "paper", "moomoo"] = "mock"
    trading_enabled: bool = False

    opend_host: str = "127.0.0.1"
    opend_port: int = 11111
    moomoo_host: str = "127.0.0.1"
    moomoo_port: int = 11111
    moomoo_market: str = "US"
    moomoo_trd_env: str = "SIMULATE"

    database_url: str = "sqlite+aiosqlite:///./data/moomoo_alpha.db"

    max_position_pct: float = 5.0
    starter_position_pct: float = 2.0
    max_risk_per_trade_pct: float = 0.5
    daily_loss_limit_pct: float = 2.0
    max_drawdown_soft_pct: float = 5.0
    max_drawdown_hard_pct: float = 8.0
    max_quote_age_seconds: int = 10
    allowed_order_types: list[str] = ["LIMIT"]
    min_equity_for_trading: float = 500.0

    universe_symbols: Any = []

    @field_validator("universe_symbols", mode="before")
    @classmethod
    def parse_universe_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(s).strip().upper() for s in parsed if str(s).strip()]
                except json.JSONDecodeError:
                    pass
            return [s.strip().upper() for s in stripped.split(",") if s.strip()]
        if not isinstance(v, list):
            return []
        return [str(s).strip().upper() for s in v if str(s).strip()]

    kline_provider: str = "yfinance"
    kline_fallback_provider: str = "yfinance"
    enable_kline_cache: bool = True
    kline_lookback_days: int = 400
    kline_extended_lookback_days: int = 1825

    log_level: str = "INFO"
    log_file: str = "data/console.log"

    data_dir: str = "data"


settings = Settings()
