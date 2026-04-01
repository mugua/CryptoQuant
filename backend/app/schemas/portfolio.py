from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class PortfolioOut(BaseModel):
    id: UUID
    user_id: UUID
    exchange: str
    total_value_usdt: Decimal
    available_usdt: Decimal
    positions: Optional[Dict[str, Any]] = None
    daily_pnl: Decimal
    total_pnl: Decimal
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioSummary(BaseModel):
    total_value_usdt: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: float
    total_pnl: Decimal
    active_positions: int
    exchanges: List[str]
