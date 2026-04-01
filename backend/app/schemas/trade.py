from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class TradeOut(BaseModel):
    id: UUID
    user_id: UUID
    strategy_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    exchange: str
    symbol: str
    side: str
    price: Decimal
    quantity: Decimal
    fee: Decimal
    fee_currency: Optional[str] = None
    pnl: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TradeStats(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: Decimal
    avg_pnl: Decimal
    max_profit: Decimal
    max_loss: Decimal
    total_fees: Decimal
