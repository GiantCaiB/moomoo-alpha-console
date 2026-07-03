from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass
class BarData:
    symbol: str
    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(Protocol):
    async def get_bars(self, symbol: str, days: int = 250) -> list[BarData]: ...
    async def get_quote(self, symbol: str) -> dict: ...
