import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate
from app.core.exceptions import NotFoundException, PermissionException

logger = logging.getLogger(__name__)


async def create_strategy(db: AsyncSession, user_id: UUID, strategy_create: StrategyCreate) -> Strategy:
    strategy = Strategy(
        user_id=user_id,
        name=strategy_create.name,
        description=strategy_create.description,
        strategy_type=strategy_create.strategy_type,
        parameters=strategy_create.parameters or {},
        is_active=True,
        is_running=False,
        exchange=strategy_create.exchange,
        symbol=strategy_create.symbol,
        timeframe=strategy_create.timeframe,
    )
    db.add(strategy)
    await db.flush()
    await db.refresh(strategy)
    logger.info(f"Strategy created: {strategy.name} for user {user_id}")
    return strategy


async def get_strategies(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 20
) -> List[Strategy]:
    result = await db.execute(
        select(Strategy).where(Strategy.user_id == user_id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_strategy(db: AsyncSession, strategy_id: UUID, user_id: UUID) -> Strategy:
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise NotFoundException("Strategy not found")
    return strategy


async def update_strategy(
    db: AsyncSession, strategy_id: UUID, user_id: UUID, update: StrategyUpdate
) -> Strategy:
    strategy = await get_strategy(db, strategy_id, user_id)
    if update.name is not None:
        strategy.name = update.name
    if update.description is not None:
        strategy.description = update.description
    if update.parameters is not None:
        strategy.parameters = update.parameters
    if update.is_active is not None:
        strategy.is_active = update.is_active
    if update.exchange is not None:
        strategy.exchange = update.exchange
    if update.symbol is not None:
        strategy.symbol = update.symbol
    if update.timeframe is not None:
        strategy.timeframe = update.timeframe
    await db.flush()
    await db.refresh(strategy)
    return strategy


async def delete_strategy(db: AsyncSession, strategy_id: UUID, user_id: UUID) -> bool:
    strategy = await get_strategy(db, strategy_id, user_id)
    if strategy.is_running:
        raise PermissionException("Cannot delete a running strategy. Stop it first.")
    await db.delete(strategy)
    await db.flush()
    return True


async def start_strategy(db: AsyncSession, strategy_id: UUID, user_id: UUID) -> Strategy:
    strategy = await get_strategy(db, strategy_id, user_id)
    if strategy.is_running:
        raise PermissionException("Strategy is already running")
    if not strategy.is_active:
        raise PermissionException("Strategy is not active")
    strategy.is_running = True
    await db.flush()
    await db.refresh(strategy)
    logger.info(f"Strategy started: {strategy.name}")
    return strategy


async def stop_strategy(db: AsyncSession, strategy_id: UUID, user_id: UUID) -> Strategy:
    strategy = await get_strategy(db, strategy_id, user_id)
    if not strategy.is_running:
        raise PermissionException("Strategy is not running")
    strategy.is_running = False
    await db.flush()
    await db.refresh(strategy)
    logger.info(f"Strategy stopped: {strategy.name}")
    return strategy
