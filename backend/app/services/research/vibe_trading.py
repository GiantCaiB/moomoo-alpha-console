"""
Vibe-Trading MCP / CLI adapter — PLACEHOLDER.

This adapter integrates with Vibe-Trading CLI or MCP server for research.
It is not required for MVP.

TODO:
  - Install vibe-trading: https://github.com/example/vibe-trading
  - Run: vibe-trading screen --universe AAPL,MSFT,NVDA
  - Parse JSON output from stdin/stdout

Usage example (when ready):
    import subprocess
    result = subprocess.run(["vibe-trading", "screen", "--universe", "AAPL,MSFT,NVDA"],
                          capture_output=True, text=True)
    signals = json.loads(result.stdout)
"""
import logging
from app.services.research.base import ResearchProvider, ScreenRequest, SignalDto, ResearchReport

logger = logging.getLogger(__name__)


class VibeTradingResearchProvider:
    async def screen_candidates(self, request: ScreenRequest) -> list[SignalDto]:
        logger.info("VibeTradingResearchProvider: not implemented (placeholder)")
        return []

    async def analyze_symbol(self, symbol: str) -> ResearchReport:
        logger.info("VibeTradingResearchProvider analyze_symbol: not implemented (placeholder)")
        return ResearchReport(symbol=symbol, summary="Not implemented", metrics={})
