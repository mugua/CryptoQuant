import logging
from typing import List, Dict, Any
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.portfolio import Portfolio
from app.models.trade import Trade
from app.schemas.portfolio import PortfolioOut, PortfolioSummary
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


async def get_portfolio_summary(db: AsyncSession, user_id: UUID) -> PortfolioSummary:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolios = list(result.scalars().all())
    if not portfolios:
        return PortfolioSummary(
            total_value_usdt=Decimal("0"),
            daily_pnl=Decimal("0"),
            daily_pnl_pct=0.0,
            total_pnl=Decimal("0"),
            active_positions=0,
            exchanges=[],
        )
    total_value = sum(p.total_value_usdt or Decimal("0") for p in portfolios)
    daily_pnl = sum(p.daily_pnl or Decimal("0") for p in portfolios)
    total_pnl = sum(p.total_pnl or Decimal("0") for p in portfolios)
    total_positions = 0
    for p in portfolios:
        if p.positions:
            total_positions += len(p.positions)
    exchanges = list({p.exchange for p in portfolios})
    daily_pnl_pct = 0.0
    if total_value > 0:
        base_value = total_value - daily_pnl
        if base_value > 0:
            daily_pnl_pct = float(daily_pnl / base_value * 100)
    return PortfolioSummary(
        total_value_usdt=total_value,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        total_pnl=total_pnl,
        active_positions=total_positions,
        exchanges=exchanges,
    )


async def get_exchange_portfolio(db: AsyncSession, user_id: UUID, exchange: str) -> PortfolioOut:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.exchange == exchange)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise NotFoundException(f"Portfolio not found for exchange: {exchange}")
    return PortfolioOut.model_validate(portfolio)


async def get_pnl_history(db: AsyncSession, user_id: UUID, days: int = 30) -> List[Dict[str, Any]]:
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import cast, Date
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id, Trade.created_at >= cutoff)
        .order_by(Trade.created_at.asc())
    )
    trades = list(result.scalars().all())
    daily_pnl: Dict[str, Decimal] = {}
    for trade in trades:
        day_key = trade.created_at.strftime("%Y-%m-%d")
        if day_key not in daily_pnl:
            daily_pnl[day_key] = Decimal("0")
        if trade.pnl is not None:
            daily_pnl[day_key] += trade.pnl
    history = []
    cumulative = Decimal("0")
    for day in sorted(daily_pnl.keys()):
        cumulative += daily_pnl[day]
        history.append({
            "date": day,
            "daily_pnl": float(daily_pnl[day]),
            "cumulative_pnl": float(cumulative),
        })
    return history
