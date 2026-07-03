from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    broker_mode: str
    broker_connected: bool
    database_ok: bool
    uptime_seconds: float
