from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.watchlist import WatchlistItemResponse, WatchlistAddRequest
from app.models.watchlist_item import WatchlistItem
from app.db.session import get_session
from app.core.config import settings

router = APIRouter()


@router.get("/api/v1/watchlist", response_model=list[WatchlistItemResponse])
async def get_watchlist(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(WatchlistItem).order_by(WatchlistItem.sort_order)
    )
    items = result.scalars().all()

    if not items:
        items = []
        for i, sym in enumerate(settings.universe_symbols):
            item = WatchlistItem(
                symbol=sym,
                list_name="default",
                sort_order=i,
            )
            session.add(item)
            items.append(item)
        await session.commit()

    return [WatchlistItemResponse(
        id=it.id, symbol=it.symbol, list_name=it.list_name,
        sort_order=it.sort_order, notes=it.notes, added_price=it.added_price,
    ) for it in items]


@router.post("/api/v1/watchlist", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    req: WatchlistAddRequest,
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(
        select(WatchlistItem).where(
            WatchlistItem.symbol == req.symbol.upper(),
            WatchlistItem.list_name == req.list_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Symbol already in watchlist")

    item = WatchlistItem(
        symbol=req.symbol.upper(),
        list_name=req.list_name,
        notes=req.notes,
    )
    session.add(item)
    await session.commit()
    return WatchlistItemResponse(
        id=item.id, symbol=item.symbol, list_name=item.list_name,
        sort_order=item.sort_order, notes=item.notes, added_price=item.added_price,
    )


@router.delete("/api/v1/watchlist/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WatchlistItem).where(WatchlistItem.symbol == symbol.upper())
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Symbol not found in watchlist")
    await session.delete(item)
    await session.commit()
    return {"success": True}
