import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.strategy_profile import StrategyProfile
from app.schemas.strategy_profile import StrategyProfileResponse

router = APIRouter(tags=["strategy-profiles"])


@router.get("/api/v1/strategy-profiles", response_model=list[StrategyProfileResponse])
async def list_strategy_profiles(
    strategy_type: str | None = Query(None, alias="type"),
    session: AsyncSession = Depends(get_session),
):
    query = select(StrategyProfile).where(StrategyProfile.is_active == True)
    if strategy_type:
        query = query.where(StrategyProfile.strategy_type == strategy_type)
    query = query.order_by(StrategyProfile.is_default.desc(), StrategyProfile.created_at.desc())

    result = await session.execute(query)
    profiles = result.scalars().all()

    return [
        _profile_to_response(p) for p in profiles
    ]


@router.get("/api/v1/strategy-profiles/{profile_id}", response_model=StrategyProfileResponse)
async def get_strategy_profile(
    profile_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(StrategyProfile).where(StrategyProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Strategy profile not found")
    return _profile_to_response(profile)


def _profile_to_response(profile: StrategyProfile) -> StrategyProfileResponse:
    return StrategyProfileResponse(
        id=profile.id,
        name=profile.name,
        strategy_type=profile.strategy_type,
        strategy_key=profile.strategy_key,
        version=profile.version,
        description=profile.description,
        parameters=json.loads(profile.parameters_json) if profile.parameters_json else None,
        rules_summary=json.loads(profile.rules_summary_json) if profile.rules_summary_json else None,
        is_default=profile.is_default,
        is_active=profile.is_active,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
