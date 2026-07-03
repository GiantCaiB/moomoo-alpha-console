from app.core.config import settings
from app.services.broker.base import BrokerHealth


def compute_broker_safety_state(broker_health: BrokerHealth | None = None) -> dict:
    mode = settings.broker_mode.lower()
    connected = broker_health.connected if broker_health else False
    trd_env = settings.moomoo_trd_env.upper().strip()
    is_moomoo = mode == "moomoo"

    if is_moomoo and connected:
        if trd_env == "REAL":
            account_env = "moomoo_real"
            data_source = "moomoo_realtime"
            is_real = True
        else:
            account_env = "moomoo_simulate"
            data_source = "moomoo_simulated"
            is_real = False
    elif is_moomoo and not connected:
        account_env = "moomoo_disconnected"
        data_source = "none"
        is_real = False
    elif mode == "paper":
        account_env = "paper"
        data_source = "paper_local"
        is_real = False
    else:
        account_env = "mock"
        data_source = "mock_synthetic"
        is_real = False

    if is_moomoo:
        is_live_trading_enabled = (
            settings.trading_enabled and trd_env == "REAL" and connected
        )
        read_only = True
    else:
        is_live_trading_enabled = settings.trading_enabled
        read_only = not settings.trading_enabled

    warnings: list[str] = []
    if is_moomoo and not connected:
        msg = broker_health.message if broker_health else "OpenD not connected"
        warnings.append(msg)
    if is_moomoo and trd_env == "REAL" and connected:
        warnings.append(
            "Read-only mode: real account data shown, but no trades can be placed"
        )
    if not settings.trading_enabled and is_moomoo and connected:
        warnings.append("Trading is disabled")

    return {
        "broker_mode": mode,
        "connected": connected,
        "data_source": data_source,
        "account_environment": account_env,
        "is_real_account_data": is_real,
        "is_live_trading_enabled": is_live_trading_enabled,
        "read_only": read_only,
        "trd_env": trd_env,
        "warnings": warnings,
        "error": broker_health.message if broker_health and not connected else None,
    }
