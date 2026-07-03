from fastapi import APIRouter, Depends

from app.schemas.position import PositionResponse
from app.services.broker.base import BrokerAdapter
from app.api.dependencies import get_broker

router = APIRouter()


@router.get("/api/v1/positions", response_model=list[PositionResponse])
async def list_positions(broker: BrokerAdapter = Depends(get_broker)):
    positions = await broker.get_positions()
    return [PositionResponse(
        id=p.symbol,
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
