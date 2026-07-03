"""
Backtrader Backtest Provider — PLACEHOLDER.

Integrates with Backtrader for strategy backtesting.
Not required for MVP.

TODO:
  - Install: pip install backtrader
  - Create strategy class extending bt.Strategy
  - Run: cerebro = bt.Cerebro(); cerebro.addstrategy(MyStrategy); cerebro.run()

Usage example (when ready):
    import backtrader as bt
    class MyStrategy(bt.Strategy):
        def next(self):
            if not self.position:
                self.buy()
"""
import logging
from app.services.research.base import ResearchProvider, ScreenRequest, SignalDto, ResearchReport

logger = logging.getLogger(__name__)


class BacktraderBacktestProvider:
    async def screen_candidates(self, request: ScreenRequest) -> list[SignalDto]:
        logger.info("BacktraderBacktestProvider: not implemented (placeholder)")
        return []

    async def analyze_symbol(self, symbol: str) -> ResearchReport:
        logger.info("BacktraderBacktestProvider analyze_symbol: not implemented (placeholder)")
        return ResearchReport(symbol=symbol, summary="Not implemented", metrics={})
