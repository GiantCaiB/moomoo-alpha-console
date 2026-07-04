import logging
from datetime import date, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False


class YFinanceKLineProvider:
    def __init__(self) -> None:
        if not YFINANCE_AVAILABLE:
            raise RuntimeError(
                "yfinance is not installed. Install it with: pip install yfinance"
            )

    def get_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjusted: bool = True,
    ) -> pd.DataFrame:
        if end_date <= start_date:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"])

        ticker = yf.Ticker(symbol)

        yf_start = start_date.isoformat()
        yf_end = (end_date + timedelta(days=1)).isoformat()

        hist = ticker.history(start=yf_start, end=yf_end, auto_adjust=False)

        if hist.empty:
            wider_end = end_date + timedelta(days=90)
            logger.info("Empty response for %s, retrying with wider range to %s", symbol, wider_end)
            yf_end_wide = (wider_end + timedelta(days=1)).isoformat()
            hist = ticker.history(start=yf_start, end=yf_end_wide, auto_adjust=False)

        if hist.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adj_close"])

        result = pd.DataFrame()
        result["date"] = hist.index.date if hasattr(hist.index, "date") else hist.index
        result["open"] = hist["Open"].values
        result["high"] = hist["High"].values
        result["low"] = hist["Low"].values
        result["close"] = hist["Close"].values
        result["volume"] = hist["Volume"].values
        result["adj_close"] = hist["Adj Close"].values if "Adj Close" in hist.columns else hist["Close"].values

        result = result[result["date"] >= start_date]
        result = result.sort_values("date").reset_index(drop=True)
        return result
