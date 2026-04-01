from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class OrderCreate(BaseModel):
    exchange: str
    symbol: str
    order_type: str
    side: str
    quantity: Decimal
    price: Optional[Decimal] = None
    strategy_id: Optional[UUID] = None


class OrderOut(BaseModel):
    id: UUID
    user_id: UUID
    strategy_id: Optional[UUID] = None
    exchange: str
    symbol: str
    order_type: str
    side: str
    price: Optional[Decimal] = None
    quantity: Decimal
    filled_quantity: Decimal
    status: str
    exchange_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
