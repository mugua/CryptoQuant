import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.backtest import BacktestRequest, BacktestResult, BacktestStats, BacktestTrade

logger = logging.getLogger(__name__)
router = APIRouter()


def _generate_ohlcv(
    start_date: datetime,
    end_date: datetime,
    timeframe: str,
    symbol: str,
) -> pd.DataFrame:
    """Generate synthetic OHLCV data for backtesting."""
    tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
    minutes = tf_minutes.get(timeframe, 60)
    freq = f"{minutes}min"
    index = pd.date_range(start=start_date, end=end_date, freq=freq, tz=timezone.utc)
    n = len(index)
    if n < 2:
        raise ValueError("Date range too short for the given timeframe")
    np.random.seed(42)
    returns = np.random.normal(0.0002, 0.02, n)
    price = 30000.0
    closes = [price]
    for r in returns[1:]:
        price = price * (1 + r)
        closes.append(max(price, 1.0))
    closes = np.array(closes)
    highs = closes * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = closes * (1 - np.abs(np.random.normal(0, 0.005, n)))
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    volumes = np.random.uniform(100, 1000, n)
    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }, index=index)
    df.index.name = "timestamp"
    return df


def _ma_cross_signals(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    fast = int(params.get("fast_period", 10))
    slow = int(params.get("slow_period", 30))
    df = df.copy()
    df["fast_ma"] = df["close"].rolling(fast).mean()
    df["slow_ma"] = df["close"].rolling(slow).mean()
    signals = pd.Series(0, index=df.index)
    cross_above = (df["fast_ma"] > df["slow_ma"]) & (df["fast_ma"].shift(1) <= df["slow_ma"].shift(1))
    cross_below = (df["fast_ma"] < df["slow_ma"]) & (df["fast_ma"].shift(1) >= df["slow_ma"].shift(1))
    signals[cross_above] = 1
    signals[cross_below] = -1
    return signals


def _rsi_signals(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    period = int(params.get("period", 14))
    overbought = float(params.get("overbought", 70))
    oversold = float(params.get("oversold", 30))
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    signals = pd.Series(0, index=df.index)
    signals[rsi < oversold] = 1
    signals[rsi > overbought] = -1
    return signals


def _macd_signals(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    fast = int(params.get("fast_period", 12))
    slow = int(params.get("slow_period", 26))
    signal_period = int(params.get("signal_period", 9))
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    signals = pd.Series(0, index=df.index)
    cross_above = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    cross_below = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
    signals[cross_above] = 1
    signals[cross_below] = -1
    return signals


def _run_backtest_engine(
    df: pd.DataFrame,
    signals: pd.Series,
    initial_capital: float,
    commission_rate: float,
) -> Dict[str, Any]:
    """Simulate trades based on signals and return performance metrics."""
    capital = initial_capital
    position = 0.0
    entry_price = 0.0
    trades: List[Dict] = []
    equity_curve: List[Dict] = []
    cumulative_pnl = 0.0

    for i, (idx, row) in enumerate(df.iterrows()):
        signal = signals.iloc[i]
        price = float(row["close"])
        equity = capital + (position * price if position > 0 else 0)
        ts_str = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
        equity_curve.append({"timestamp": ts_str, "equity": equity})

        if signal == 1 and position == 0:
            # Buy
            qty = (capital * 0.99) / price
            fee = qty * price * commission_rate
            capital -= qty * price + fee
            position = qty
            entry_price = price
        elif signal == -1 and position > 0:
            # Sell
            gross = position * price
            fee = gross * commission_rate
            pnl = gross - fee - (position * entry_price)
            capital += gross - fee
            cumulative_pnl += pnl
            trades.append({
                "timestamp": idx,
                "side": "sell",
                "price": Decimal(str(round(price, 8))),
                "quantity": Decimal(str(round(position, 8))),
                "fee": Decimal(str(round(fee, 8))),
                "pnl": Decimal(str(round(pnl, 8))),
                "cumulative_pnl": Decimal(str(round(cumulative_pnl, 8))),
            })
            position = 0.0
            entry_price = 0.0

    # Close open position at end
    if position > 0:
        price = float(df["close"].iloc[-1])
        gross = position * price
        fee = gross * commission_rate
        pnl = gross - fee - (position * entry_price)
        capital += gross - fee
        cumulative_pnl += pnl
        trades.append({
            "timestamp": df.index[-1],
            "side": "sell",
            "price": Decimal(str(round(price, 8))),
            "quantity": Decimal(str(round(position, 8))),
            "fee": Decimal(str(round(fee, 8))),
            "pnl": Decimal(str(round(pnl, 8))),
            "cumulative_pnl": Decimal(str(round(cumulative_pnl, 8))),
        })

    final_capital = capital
    total_return = (final_capital - initial_capital) / initial_capital * 100

    # Calculate statistics
    pnl_values = [float(t["pnl"]) for t in trades]
    winning_trades = [p for p in pnl_values if p > 0]
    losing_trades = [p for p in pnl_values if p < 0]
    total_trades = len(trades)
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    profit_factor = (
        sum(winning_trades) / abs(sum(losing_trades))
        if losing_trades and sum(winning_trades) > 0
        else 0.0
    )

    # Max drawdown from equity curve
    equities = np.array([e["equity"] for e in equity_curve])
    rolling_max = np.maximum.accumulate(equities)
    drawdowns = (equities - rolling_max) / rolling_max
    max_drawdown = float(abs(drawdowns.min())) if len(drawdowns) > 0 else 0.0

    # Annualized return
    days = (df.index[-1] - df.index[0]).days if len(df) > 1 else 1
    annual_return = ((1 + total_return / 100) ** (365 / max(days, 1)) - 1) * 100

    # Sharpe ratio (assuming risk-free rate = 0)
    daily_returns = pd.Series(equities).pct_change().dropna()
    sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0.0

    # Sortino ratio
    downside = daily_returns[daily_returns < 0]
    sortino = float(daily_returns.mean() / downside.std() * np.sqrt(252)) if len(downside) > 0 and downside.std() > 0 else 0.0

    # Calmar ratio
    calmar = annual_return / (max_drawdown * 100) if max_drawdown > 0 else 0.0

    total_fees = sum(float(t["fee"]) for t in trades)

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "stats": {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "profit_factor": profit_factor,
            "avg_trade_duration": 0.0,
            "total_fees": Decimal(str(round(total_fees, 8))),
            "final_capital": Decimal(str(round(final_capital, 8))),
        },
    }


@router.post("/run", response_model=BacktestResult)
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a backtest for a given strategy configuration."""
    df = _generate_ohlcv(request.start_date, request.end_date, request.timeframe, request.symbol)
    strategy_type = request.strategy_type.upper()
    if strategy_type == "MA_CROSS":
        signals = _ma_cross_signals(df, request.parameters)
    elif strategy_type == "RSI":
        signals = _rsi_signals(df, request.parameters)
    elif strategy_type == "MACD":
        signals = _macd_signals(df, request.parameters)
    else:
        signals = _ma_cross_signals(df, request.parameters)

    result = _run_backtest_engine(
        df, signals, float(request.initial_capital), request.commission_rate
    )

    backtest_trades = [
        BacktestTrade(
            timestamp=t["timestamp"],
            side=t["side"],
            price=t["price"],
            quantity=t["quantity"],
            fee=t["fee"],
            pnl=t["pnl"],
            cumulative_pnl=t["cumulative_pnl"],
        )
        for t in result["trades"]
    ]

    stats = BacktestStats(**result["stats"])

    return BacktestResult(
        strategy_type=request.strategy_type,
        parameters=request.parameters,
        exchange=request.exchange,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        stats=stats,
        trades=backtest_trades,
        equity_curve=result["equity_curve"],
    )
