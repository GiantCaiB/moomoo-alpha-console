from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.position import PositionResponse
from app.models.position import Position
from app.db.session import get_session

router = APIRouter()


@router.get("/api/v1/positions", response_model=list[PositionResponse])
async def list_positions(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Position).where(Position.status == "OPEN"))
    positions = result.scalars().all()
    return [PositionResponse(
        id=p.id,
        symbol=p.symbol,
        quantity=p.quantity,
        avg_cost=p.avg_cost,
        current_price=p.current_price,
        unrealized_pnl=p.unrealized_pnl,
        day_pnl=p.day_pnl,
        stop_level=p.stop_level,
        position_pct=p.position_pct,
        status=p.status,
    ) for p in positions]
