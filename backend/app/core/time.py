from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

US_MARKET_TZ = ZoneInfo("America/New_York")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_eastern() -> datetime:
    return datetime.now(US_MARKET_TZ)


def is_market_hours(dt: datetime | None = None) -> bool:
    if dt is None:
        dt = now_eastern()
    weekday = dt.weekday()
    if weekday >= 5:
        return False
    t = dt.time()
    return (t.hour >= 9 and t.minute >= 30) and t.hour < 16


def is_premarket(dt: datetime | None = None) -> bool:
    if dt is None:
        dt = now_eastern()
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    return 4 <= t.hour < 9 or (t.hour == 9 and t.minute < 30)


def is_postmarket(dt: datetime | None = None) -> bool:
    if dt is None:
        dt = now_eastern()
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    return t.hour >= 16


def is_data_fresh(updated_at: datetime, max_age_seconds: int = 10) -> bool:
    return (now_utc() - updated_at).total_seconds() < max_age_seconds


def format_timestamp(dt: datetime) -> str:
    return dt.astimezone(US_MARKET_TZ).strftime("%Y-%m-%d %H:%M:%S ET")
