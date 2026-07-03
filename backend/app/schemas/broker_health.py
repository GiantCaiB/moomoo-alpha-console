from pydantic import BaseModel


class BrokerHealthResponse(BaseModel):
    broker_mode: str
    connected: bool
    data_source: str
    account_environment: str
    is_real_account_data: bool
    is_live_trading_enabled: bool
    read_only: bool
    opend_host: str
    opend_port: int
    trd_env: str
    warnings: list[str]
    error: str | None
