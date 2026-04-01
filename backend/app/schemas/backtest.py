from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class BacktestRequest(BaseModel):
    strategy_id: Optional[UUID] = None
    strategy_type: str
    parameters: Dict[str, Any] = {}
    exchange: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("10000")
    commission_rate: float = 0.001


class BacktestTrade(BaseModel):
    timestamp: datetime
    side: str
    price: Decimal
    quantity: Decimal
    fee: Decimal
    pnl: Decimal
    cumulative_pnl: Decimal


class BacktestStats(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    avg_trade_duration: float
    total_fees: Decimal
    final_capital: Decimal


class BacktestResult(BaseModel):
    strategy_type: str
    parameters: Dict[str, Any]
    exchange: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    stats: BacktestStats
    trades: List[BacktestTrade]
    equity_curve: List[Dict[str, Any]]
