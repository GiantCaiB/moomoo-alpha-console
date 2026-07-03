import random
from datetime import date, timedelta
from app.services.market_data.base import MarketDataProvider, BarData
from app.services.broker.mock import BASE_PRICES


class MockMarketDataProvider:
    async def get_bars(self, symbol: str, days: int = 250) -> list[BarData]:
        base = BASE_PRICES.get(symbol, 100.0)
        bars: list[BarData] = []
        price = base * 0.85
        d = date.today() - timedelta(days=days)
        for _ in range(days):
            change = random.gauss(0.001, 0.02)
            price = price * (1 + change)
            bars.append(BarData(
                symbol=symbol,
                bar_date=d,
                open=round(price * 0.99, 2),
                high=round(price * 1.02, 2),
                low=round(price * 0.98, 2),
                close=round(price, 2),
                volume=random.randint(500000, 10000000),
            ))
            d += timedelta(days=1)
        return bars

    async def get_quote(self, symbol: str) -> dict:
        base = BASE_PRICES.get(symbol, 100.0)
        return {"symbol": symbol, "last": base, "bid": base * 0.999, "ask": base * 1.001}
