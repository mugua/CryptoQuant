import logging
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.order import Order
from app.models.trade import Trade
from app.schemas.order import OrderCreate
from app.schemas.trade import TradeStats
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


async def create_order(db: AsyncSession, user_id: UUID, order_create: OrderCreate) -> Order:
    if order_create.order_type == "limit" and order_create.price is None:
        raise ValidationException("Limit orders require a price")
    order = Order(
        user_id=user_id,
        strategy_id=order_create.strategy_id,
        exchange=order_create.exchange,
        symbol=order_create.symbol,
        order_type=order_create.order_type,
        side=order_create.side,
        price=order_create.price,
        quantity=order_create.quantity,
        filled_quantity=Decimal("0"),
        status="pending",
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)
    logger.info(f"Order created: {order.id} for user {user_id}")
    return order


async def get_orders(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 20
) -> List[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_order(db: AsyncSession, order_id: UUID, user_id: UUID) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundException("Order not found")
    return order


async def cancel_order(db: AsyncSession, order_id: UUID, user_id: UUID) -> Order:
    order = await get_order(db, order_id, user_id)
    if order.status in ("filled", "cancelled"):
        raise ValidationException(f"Cannot cancel order with status: {order.status}")
    order.status = "cancelled"
    await db.flush()
    await db.refresh(order)
    logger.info(f"Order cancelled: {order.id}")
    return order


async def get_trades(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 20
) -> List[Trade]:
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_trade_stats(db: AsyncSession, user_id: UUID) -> TradeStats:
    result = await db.execute(
        select(Trade).where(Trade.user_id == user_id)
    )
    trades = list(result.scalars().all())
    if not trades:
        return TradeStats(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=Decimal("0"),
            avg_pnl=Decimal("0"),
            max_profit=Decimal("0"),
            max_loss=Decimal("0"),
            total_fees=Decimal("0"),
        )
    total_trades = len(trades)
    pnl_values = [t.pnl for t in trades if t.pnl is not None]
    winning_trades = sum(1 for p in pnl_values if p > 0)
    losing_trades = sum(1 for p in pnl_values if p < 0)
    total_pnl = sum(pnl_values, Decimal("0"))
    avg_pnl = total_pnl / len(pnl_values) if pnl_values else Decimal("0")
    max_profit = max(pnl_values) if pnl_values else Decimal("0")
    max_loss = min(pnl_values) if pnl_values else Decimal("0")
    total_fees = sum((t.fee for t in trades if t.fee is not None), Decimal("0"))
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    return TradeStats(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        total_pnl=total_pnl,
        avg_pnl=avg_pnl,
        max_profit=max_profit,
        max_loss=max_loss,
        total_fees=total_fees,
    )
