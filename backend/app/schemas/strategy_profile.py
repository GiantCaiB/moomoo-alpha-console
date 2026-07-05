from datetime import datetime
from pydantic import BaseModel


class StrategyProfileResponse(BaseModel):
    id: str
    name: str
    strategy_type: str
    strategy_key: str
    version: str
    description: str | None = None
    parameters: dict | None = None
    rules_summary: dict | None = None
    is_default: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class StrategyProfileListResponse(BaseModel):
    profiles: list[StrategyProfileResponse]
