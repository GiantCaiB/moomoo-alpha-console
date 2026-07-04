from typing import Protocol, runtime_checkable
from datetime import date

import pandas as pd


@runtime_checkable
class KLineProvider(Protocol):
    def get_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjusted: bool = True,
    ) -> pd.DataFrame:
        ...


def check_kline_columns(df: pd.DataFrame) -> None:
    required = {"date", "open", "high", "low", "close", "volume", "adj_close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"KLineProvider returned DataFrame missing columns: {missing}")
