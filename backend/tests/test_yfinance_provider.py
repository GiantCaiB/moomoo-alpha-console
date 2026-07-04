"""Tests for YFinanceKLineProvider.

Uses mock patching of yfinance to avoid live internet.
Tests:
- Exclusive end date handling
- Short empty response retries wider range
- Adjusted vs unadjusted close
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd

from app.services.kline.yfinance_provider import YFinanceKLineProvider


def _mock_history(days: int = 260, start: date = date(2024, 1, 1)) -> pd.DataFrame:
    """Create a mock yfinance history DataFrame."""
    dates = pd.date_range(start=start, periods=days, freq="D")
    price = 100.0
    opens, highs, lows, closes, adj_closes, volumes = [], [], [], [], [], []
    for i in range(days):
        price *= 1.001
        opens.append(round(price * 0.99, 2))
        highs.append(round(price * 1.02, 2))
        lows.append(round(price * 0.98, 2))
        closes.append(round(price, 2))
        adj_closes.append(round(price * 0.99, 2))
        volumes.append(1_000_000 + i * 1000)

    return pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": volumes,
        "Adj Close": adj_closes,
    }, index=dates)


@pytest.mark.asyncio
async def test_exclusive_end_date():
    """End date should be exclusive in yfinance; provider handles this."""
    provider = YFinanceKLineProvider()

    mock_ticker = MagicMock()
    mock_hist = _mock_history(days=10, start=date(2024, 1, 1))

    with patch("yfinance.Ticker", return_value=mock_ticker):
        mock_ticker.history.return_value = mock_hist

        df = provider.get_daily_bars(
            "AAPL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10),
            adjusted=True,
        )

        # Should have rows from Jan 1 to Jan 10
        assert not df.empty
        call_kwargs = mock_ticker.history.call_args[1]
        assert "end" in call_kwargs


@pytest.mark.asyncio
async def test_short_empty_retry():
    """If yfinance returns empty, provider retries with wider range."""
    provider = YFinanceKLineProvider()

    mock_ticker = MagicMock()
    # First call returns empty, second returns data
    hist_data = _mock_history(days=100, start=date(2024, 1, 1))
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return pd.DataFrame()
        return hist_data

    mock_ticker.history.side_effect = side_effect

    with patch("yfinance.Ticker", return_value=mock_ticker):
        df = provider.get_daily_bars(
            "AAPL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            adjusted=True,
        )

        assert not df.empty
        assert call_count[0] >= 2


@pytest.mark.asyncio
async def test_adjusted_vs_unadjusted():
    """Adjusted close should differ from close when provider adjusts."""
    provider = YFinanceKLineProvider()

    mock_ticker = MagicMock()
    mock_hist = _mock_history(days=50, start=date(2024, 1, 1))
    # Ensure adj_close differs from close
    mock_hist["Adj Close"] = mock_hist["Close"] * 0.98

    with patch("yfinance.Ticker", return_value=mock_ticker):
        mock_ticker.history.return_value = mock_hist

        df = provider.get_daily_bars(
            "AAPL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 20),
            adjusted=True,
        )

        assert not df.empty
        assert "adj_close" in df.columns
        # adj_close should be present
        assert df["adj_close"].iloc[0] != df["close"].iloc[0]


@pytest.mark.asyncio
async def test_no_yfinance_raises():
    """If yfinance not installed, provider should fail clearly."""
    with patch("app.services.kline.yfinance_provider.YFINANCE_AVAILABLE", False):
        with pytest.raises(RuntimeError, match="yfinance is not installed"):
            YFinanceKLineProvider()
