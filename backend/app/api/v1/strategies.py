import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate, StrategyOut
from app.services import strategy_service
from app.utils.helpers import make_paginated_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=dict)
async def list_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    strategies = await strategy_service.get_strategies(db, current_user.id, skip, limit)
    count_result = await db.execute(
        select(func.count(Strategy.id)).where(Strategy.user_id == current_user.id)
    )
    total = count_result.scalar_one() or 0
    items = [StrategyOut.model_validate(s) for s in strategies]
    return make_paginated_response(items, total, skip, limit)


@router.post("", response_model=StrategyOut, status_code=201)
async def create_strategy(
    strategy_create: StrategyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await strategy_service.create_strategy(db, current_user.id, strategy_create)
    return strategy


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await strategy_service.get_strategy(db, strategy_id, current_user.id)


@router.put("/{strategy_id}", response_model=StrategyOut)
async def update_strategy(
    strategy_id: UUID,
    strategy_update: StrategyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await strategy_service.update_strategy(db, strategy_id, current_user.id, strategy_update)


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await strategy_service.delete_strategy(db, strategy_id, current_user.id)


@router.post("/{strategy_id}/start", response_model=StrategyOut)
async def start_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await strategy_service.start_strategy(db, strategy_id, current_user.id)


@router.post("/{strategy_id}/stop", response_model=StrategyOut)
async def stop_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await strategy_service.stop_strategy(db, strategy_id, current_user.id)
