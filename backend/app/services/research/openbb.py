"""
OpenBB Research Provider — PLACEHOLDER.

Integrates with OpenBB Platform for fundamental and technical research.
Not required for MVP.

TODO:
  - Install: pip install openbb[all]
  - Use: from openbb import obb
  - Example: obb.equity.price.historical("AAPL", provider="yfinance")

Usage example (when ready):
    from openbb import obb
    data = obb.equity.price.historical("AAPL", provider="yfinance")
"""
import logging
from app.services.research.base import ResearchProvider, ScreenRequest, SignalDto, ResearchReport

logger = logging.getLogger(__name__)


class OpenBBResearchProvider:
    async def screen_candidates(self, request: ScreenRequest) -> list[SignalDto]:
        logger.info("OpenBBResearchProvider: not implemented (placeholder)")
        return []

    async def analyze_symbol(self, symbol: str) -> ResearchReport:
        logger.info("OpenBBResearchProvider analyze_symbol: not implemented (placeholder)")
        return ResearchReport(symbol=symbol, summary="Not implemented", metrics={})
