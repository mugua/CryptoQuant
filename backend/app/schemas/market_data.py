from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal


class CandlestickData(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class MarketTicker(BaseModel):
    exchange: str
    symbol: str
    last: Decimal
    bid: Decimal
    ask: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal
    change: Decimal
    change_pct: float
    timestamp: datetime


class OrderBook(BaseModel):
    exchange: str
    symbol: str
    bids: List[List[Decimal]]
    asks: List[List[Decimal]]
    timestamp: datetime
