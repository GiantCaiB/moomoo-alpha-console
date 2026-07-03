from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Moomoo Alpha Console"
    debug: bool = True

    broker_mode: Literal["mock", "paper", "moomoo"] = "mock"
    trading_enabled: bool = False

    opend_host: str = "127.0.0.1"
    opend_port: int = 11111

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

    universe_symbols: list[str] = [
        "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN",
        "META", "GOOGL", "TSLA", "AMD", "AVGO", "COST", "NFLX",
    ]

    log_level: str = "INFO"
    log_file: str = "data/console.log"

    data_dir: str = "data"


settings = Settings()
