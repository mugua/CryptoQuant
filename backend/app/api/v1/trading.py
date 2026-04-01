import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.order import Order
from app.models.trade import Trade
from app.schemas.order import OrderCreate, OrderOut
from app.schemas.trade import TradeOut, TradeStats
from app.services import order_service
from app.utils.helpers import make_paginated_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/orders", response_model=OrderOut, status_code=201)
async def place_order(
    order_create: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.create_order(db, current_user.id, order_create)
    return order


@router.get("/orders")
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    orders = await order_service.get_orders(db, current_user.id, skip, limit)
    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.user_id == current_user.id)
    )
    total = count_result.scalar_one() or 0
    items = [OrderOut.model_validate(o) for o in orders]
    return make_paginated_response(items, total, skip, limit)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.get_order(db, order_id, current_user.id)


@router.delete("/orders/{order_id}", response_model=OrderOut)
async def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.cancel_order(db, order_id, current_user.id)


@router.get("/trades")
async def list_trades(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    trades = await order_service.get_trades(db, current_user.id, skip, limit)
    count_result = await db.execute(
        select(func.count(Trade.id)).where(Trade.user_id == current_user.id)
    )
    total = count_result.scalar_one() or 0
    stats = await order_service.get_trade_stats(db, current_user.id)
    items = [TradeOut.model_validate(t) for t in trades]
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total,
        "stats": stats,
    }
