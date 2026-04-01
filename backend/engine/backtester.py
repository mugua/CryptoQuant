"""
Event-driven backtester with commission, slippage, and comprehensive metrics.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from engine.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a single backtest run.

    Parameters
    ----------
    start_date : datetime
    end_date : datetime
    initial_capital : float
    commission_rate : float
        Fraction of trade value charged as commission (default 0.001 = 0.1 %).
    slippage : float
        Fraction of price applied as adverse slippage on fills (default 0.001).
    exchange : str
    symbol : str
    timeframe : str
        ccxt-compatible timeframe string, e.g. ``"1h"``.
    """

    start_date: datetime
    end_date: datetime
    initial_capital: float = 10_000.0
    commission_rate: float = 0.001
    slippage: float = 0.001
    exchange: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"


@dataclass
class Trade:
    """Record of a completed round-trip trade."""

    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # "long" | "short"
    quantity: float
    entry_price: float
    exit_price: float
    commission: float
    pnl: float
    pnl_pct: float
    duration_hours: float


@dataclass
class BacktestResult:
    """Full result of a backtest run."""

    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Optional[BacktestConfig] = None


class Backtester:
    """
    Event-driven backtester.

    Usage::

        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
        )
        result = Backtester().run(strategy, config, ohlcv_df)
    """

    def run(
        self,
        strategy: StrategyBase,
        config: BacktestConfig,
        ohlcv: pd.DataFrame,
    ) -> BacktestResult:
        """
        Execute the backtest.

        Parameters
        ----------
        strategy : StrategyBase
            An uninitialised strategy instance (``initialize()`` will be
            called internally).
        config : BacktestConfig
        ohlcv : pd.DataFrame
            OHLCV DataFrame with columns: open, high, low, close, volume
            and a DatetimeIndex.  Must already be filtered to the desired
            date range.

        Returns
        -------
        BacktestResult
        """
        if ohlcv.empty:
            raise ValueError("OHLCV DataFrame is empty.")

        # Inject capital and initialise strategy.
        strategy._set_capital(config.initial_capital)
        strategy.initialize()

        capital = config.initial_capital
        position: float = 0.0
        entry_price: float = 0.0
        entry_time: Optional[datetime] = None

        equity_records: Dict[datetime, float] = {}
        trades: List[Trade] = []
        total_commission: float = 0.0

        for ts, candle in ohlcv.iterrows():
            close = float(candle["close"])

            # Let the strategy observe this candle.
            signal = strategy.on_candle(candle)

            # Equity snapshot (mark-to-market).
            equity = capital + position * close
            equity_records[ts] = equity

            if signal is None:
                continue

            sig_type = signal.signal_type.value if hasattr(signal.signal_type, "value") else str(signal.signal_type)

            if sig_type in ("buy", "BUY") and position == 0:
                fill_price = close * (1 + config.slippage)
                quantity = signal.quantity if signal.quantity > 0 else (capital * 0.99) / fill_price
                cost = quantity * fill_price
                commission = cost * config.commission_rate
                if cost + commission > capital:
                    quantity = (capital / (fill_price * (1 + config.commission_rate))) * 0.99
                    cost = quantity * fill_price
                    commission = cost * config.commission_rate

                capital -= cost + commission
                position = quantity
                entry_price = fill_price
                entry_time = ts
                total_commission += commission
                logger.debug("BUY  %s qty=%.6f @ %.2f  capital=%.2f", config.symbol, quantity, fill_price, capital)

            elif sig_type in ("sell", "SELL", "close", "CLOSE") and position > 0:
                fill_price = close * (1 - config.slippage)
                quantity = position
                proceeds = quantity * fill_price
                commission = proceeds * config.commission_rate
                capital += proceeds - commission
                total_commission += commission

                gross_entry = quantity * entry_price
                pnl = proceeds - commission - gross_entry
                pnl_pct = pnl / gross_entry * 100 if gross_entry else 0.0
                duration = (
                    (ts - entry_time).total_seconds() / 3600
                    if entry_time is not None
                    else 0.0
                )
                trades.append(
                    Trade(
                        entry_time=entry_time or ts,
                        exit_time=ts,
                        symbol=config.symbol,
                        side="long",
                        quantity=quantity,
                        entry_price=entry_price,
                        exit_price=fill_price,
                        commission=commission,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        duration_hours=duration,
                    )
                )
                logger.debug("SELL %s qty=%.6f @ %.2f  pnl=%.2f  capital=%.2f", config.symbol, quantity, fill_price, pnl, capital)
                position = 0.0
                entry_price = 0.0
                entry_time = None

        # Force-close any open position at the last candle.
        if position > 0:
            last_close = float(ohlcv["close"].iloc[-1])
            fill_price = last_close * (1 - config.slippage)
            proceeds = position * fill_price
            commission = proceeds * config.commission_rate
            capital += proceeds - commission
            total_commission += commission
            pnl = proceeds - commission - position * entry_price
            pnl_pct = pnl / (position * entry_price) * 100 if entry_price else 0.0
            duration = (
                (ohlcv.index[-1] - entry_time).total_seconds() / 3600
                if entry_time is not None
                else 0.0
            )
            trades.append(
                Trade(
                    entry_time=entry_time or ohlcv.index[-1],
                    exit_time=ohlcv.index[-1],
                    symbol=config.symbol,
                    side="long",
                    quantity=position,
                    entry_price=entry_price,
                    exit_price=fill_price,
                    commission=commission,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    duration_hours=duration,
                )
            )
            position = 0.0

        equity_series = pd.Series(equity_records, dtype=float)
        equity_series.index = pd.to_datetime(equity_series.index)
        stats = self._calculate_stats(
            trades=trades,
            equity_curve=equity_series,
            initial_capital=config.initial_capital,
            final_capital=capital,
            config=config,
            total_commission=total_commission,
        )

        return BacktestResult(trades=trades, equity_curve=equity_series, stats=stats, config=config)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_stats(
        trades: List[Trade],
        equity_curve: pd.Series,
        initial_capital: float,
        final_capital: float,
        config: BacktestConfig,
        total_commission: float,
    ) -> Dict[str, Any]:
        n = len(trades)
        pnl_list = [t.pnl for t in trades]
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p < 0]

        total_return = (final_capital - initial_capital) / initial_capital * 100
        days = max((config.end_date - config.start_date).days, 1)
        ann_return = ((1 + total_return / 100) ** (365.0 / days) - 1) * 100

        # Max drawdown.
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        max_drawdown = float(abs(drawdown.min())) if not drawdown.empty else 0.0

        # Sharpe ratio (annualised, rf=0).
        daily_ret = equity_curve.resample("D").last().pct_change().dropna()
        sharpe = (
            float(daily_ret.mean() / daily_ret.std() * math.sqrt(252))
            if daily_ret.std() > 0
            else 0.0
        )

        # Sortino ratio.
        neg_ret = daily_ret[daily_ret < 0]
        sortino = (
            float(daily_ret.mean() / neg_ret.std() * math.sqrt(252))
            if len(neg_ret) > 0 and neg_ret.std() > 0
            else 0.0
        )

        # Calmar ratio.
        calmar = ann_return / (max_drawdown * 100) if max_drawdown > 0 else 0.0

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        avg_duration = (
            sum(t.duration_hours for t in trades) / n if n else 0.0
        )

        return {
            "total_trades": n,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / n if n else 0.0,
            "total_return": total_return,
            "annualized_return": ann_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "profit_factor": profit_factor,
            "avg_trade_duration_hours": avg_duration,
            "total_commission": total_commission,
            "initial_capital": initial_capital,
            "final_capital": final_capital,
        }
