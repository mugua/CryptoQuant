import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.portfolio import PortfolioOut, PortfolioSummary
from app.services import portfolio_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await portfolio_service.get_portfolio_summary(db, current_user.id)


@router.get("/pnl-history")
async def get_pnl_history(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    history = await portfolio_service.get_pnl_history(db, current_user.id, days)
    return {"history": history, "days": days}


@router.get("/{exchange}", response_model=PortfolioOut)
async def get_exchange_portfolio(
    exchange: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await portfolio_service.get_exchange_portfolio(db, current_user.id, exchange)


@router.get("/{exchange}/positions")
async def get_positions(
    exchange: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await portfolio_service.get_exchange_portfolio(db, current_user.id, exchange)
    return {"exchange": exchange, "positions": portfolio.positions or {}}
