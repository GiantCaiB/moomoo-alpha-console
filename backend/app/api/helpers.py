from sqlalchemy.ext.asyncio import AsyncSession

from app.services.settings.trading_universe import TradingUniverseResolver
resolver = TradingUniverseResolver()


async def resolve_trading_universe(session: AsyncSession) -> tuple[list[str], str]:
    state = await resolver.resolve(session)
    return state.symbols, state.source


async def get_active_universe(session: AsyncSession) -> list[str]:
    symbols, _ = await resolve_trading_universe(session)
    return symbols
