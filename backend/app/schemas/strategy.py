from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class StrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    strategy_type: str
    parameters: Optional[Dict[str, Any]] = {}
    exchange: str
    symbol: str
    timeframe: str


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    exchange: Optional[str] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None


class StrategyOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    strategy_type: str
    parameters: Optional[Dict[str, Any]] = None
    is_active: bool
    is_running: bool
    exchange: str
    symbol: str
    timeframe: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyRun(BaseModel):
    dry_run: bool = True
