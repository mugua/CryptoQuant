from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class AlertCreate(BaseModel):
    name: str
    alert_type: str
    exchange: str
    symbol: str
    condition: str
    threshold: Decimal
    is_active: bool = True


class AlertUpdate(BaseModel):
    name: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[Decimal] = None
    is_active: Optional[bool] = None


class AlertOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    alert_type: str
    exchange: str
    symbol: str
    condition: str
    threshold: Decimal
    is_active: bool
    is_triggered: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
