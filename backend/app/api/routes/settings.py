import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.app_setting import AppSetting
from app.schemas.settings import TradingUniverseRequest, TradingUniverseResponse
from app.services.settings.trading_universe import TradingUniverseResolver

logger = logging.getLogger(__name__)

router = APIRouter()
resolver = TradingUniverseResolver()


@router.get("/api/v1/settings/trading-universe", response_model=TradingUniverseResponse)
async def get_trading_universe(session: AsyncSession = Depends(get_session)):
    state = await resolver.resolve(session)
    return TradingUniverseResponse(symbols=state.symbols, source=state.source)


@router.put("/api/v1/settings/trading-universe", response_model=TradingUniverseResponse)
async def save_trading_universe(
    req: TradingUniverseRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        deduped = resolver.validate_symbols(req.symbols)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = await session.execute(
        select(AppSetting).where(AppSetting.key == "trading_universe")
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = AppSetting(
            key="trading_universe",
            value=json.dumps(deduped),
            description="User-defined trading universe for screener and watchlist",
        )
        session.add(row)
    else:
        row.value = json.dumps(deduped)
        row.description = "User-defined trading universe for screener and watchlist"

    await session.commit()

    return TradingUniverseResponse(symbols=deduped, source="database")


@router.delete("/api/v1/settings/trading-universe")
async def delete_trading_universe(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(AppSetting).where(AppSetting.key == "trading_universe")
    )
    row = result.scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()
    return {"success": True}
