from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    content: str
    notification_type: str
    is_read: bool
    related_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferences(BaseModel):
    email_enabled: bool = True
    push_enabled: bool = True
    trade_alerts: bool = True
    price_alerts: bool = True
    system_alerts: bool = True
