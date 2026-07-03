from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.portfolio import PortfolioSummary
from app.services.portfolio.service import get_portfolio_summary
from app.services.broker.base import BrokerAdapter
from app.db.session import get_session
from app.api.dependencies import get_broker

router = APIRouter()


@router.get("/api/v1/portfolio/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    broker: BrokerAdapter = Depends(get_broker),
):
    data = await get_portfolio_summary(broker)
    return PortfolioSummary(**data)
