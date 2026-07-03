"""
Shared dependencies for FastAPI route injection.

Keeps get_broker() and get_risk_engine() in a separate module
to avoid circular imports between app.main and app.api.routes.*
"""
from app.services.broker.base import BrokerAdapter
from app.services.risk.engine import RiskEngine

# These are set by app.main on startup
_broker: BrokerAdapter | None = None
_risk_engine: RiskEngine | None = None


def set_broker(broker: BrokerAdapter) -> None:
    global _broker
    _broker = broker


def set_risk_engine(engine: RiskEngine) -> None:
    global _risk_engine
    _risk_engine = engine


def get_broker() -> BrokerAdapter:
    if _broker is None:
        raise RuntimeError("Broker not initialized")
    return _broker


def get_risk_engine() -> RiskEngine:
    if _risk_engine is None:
        raise RuntimeError("Risk engine not initialized")
    return _risk_engine
