"""
Moving Average Crossover strategy.

Generates buy signals when the fast MA crosses above the slow MA and sell
signals when the fast MA crosses below the slow MA.  Position sizing is
based on the Average True Range (ATR).
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional

import pandas as pd

from engine.strategy_base import Signal, SignalType, StrategyBase
from engine import indicators as ind


class MovingAverageCross(StrategyBase):
    """
    Dual moving-average crossover strategy.

    Parameters
    ----------
    fast_period : int
        Period for the fast moving average (default 9).
    slow_period : int
        Period for the slow moving average (default 21).
    signal_type : str
        ``"ema"`` or ``"sma"`` (default ``"ema"``).
    atr_period : int
        ATR period for position sizing (default 14).
    atr_multiplier : float
        Fraction of ATR used to size positions (default 1.0).
    risk_per_trade_pct : float
        Fraction of capital risked per trade (default 0.01 = 1 %).
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="MovingAverageCross",
            version="1.0.0",
            description="Buy/sell on fast MA vs slow MA crossovers; size via ATR.",
            parameters=parameters or {},
        )
        self._fast_period: int = int(self._get_param("fast_period", 9))
        self._slow_period: int = int(self._get_param("slow_period", 21))
        self._signal_type: str = str(self._get_param("signal_type", "ema")).lower()
        self._atr_period: int = int(self._get_param("atr_period", 14))
        self._atr_multiplier: float = float(self._get_param("atr_multiplier", 1.0))
        self._risk_per_trade_pct: float = float(self._get_param("risk_per_trade_pct", 0.01))

        # Warm-up buffers.
        buf_size = self._slow_period + self._atr_period + 10
        self._highs: Deque[float] = deque(maxlen=buf_size)
        self._lows: Deque[float] = deque(maxlen=buf_size)
        self._closes: Deque[float] = deque(maxlen=buf_size)
        self._volumes: Deque[float] = deque(maxlen=buf_size)

        self._prev_fast_ma: Optional[float] = None
        self._prev_slow_ma: Optional[float] = None

    def initialize(self) -> None:
        """Reset warm-up buffers (called by the backtester)."""
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()
        self._volumes.clear()
        self._prev_fast_ma = None
        self._prev_slow_ma = None

    def on_candle(self, candle: pd.Series) -> Optional[Signal]:
        """
        Process a new closed candle and return a signal when a crossover occurs.

        Parameters
        ----------
        candle : pd.Series
            Must contain: open, high, low, close, volume.

        Returns
        -------
        Signal or None
        """
        self._highs.append(float(candle["high"]))
        self._lows.append(float(candle["low"]))
        self._closes.append(float(candle["close"]))
        self._volumes.append(float(candle.get("volume", 0.0)))

        if len(self._closes) < self._slow_period:
            return None

        closes_s = pd.Series(list(self._closes))

        if self._signal_type == "sma":
            fast_series = ind.SMA(closes_s, self._fast_period)
            slow_series = ind.SMA(closes_s, self._slow_period)
        else:
            fast_series = ind.EMA(closes_s, self._fast_period)
            slow_series = ind.EMA(closes_s, self._slow_period)

        fast_ma = float(fast_series.iloc[-1])
        slow_ma = float(slow_series.iloc[-1])

        if pd.isna(fast_ma) or pd.isna(slow_ma):
            self._prev_fast_ma = fast_ma
            self._prev_slow_ma = slow_ma
            return None

        signal: Optional[Signal] = None
        close = float(candle["close"])
        position = self.get_position(self._get_param("symbol", "BTC/USDT"))
        has_position = position is not None and position.is_open

        if self._prev_fast_ma is not None and self._prev_slow_ma is not None:
            crossed_above = (
                self._prev_fast_ma <= self._prev_slow_ma and fast_ma > slow_ma
            )
            crossed_below = (
                self._prev_fast_ma >= self._prev_slow_ma and fast_ma < slow_ma
            )

            if crossed_above and not has_position:
                quantity = self._calc_quantity(close)
                signal = Signal(
                    symbol=str(self._get_param("symbol", "BTC/USDT")),
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=quantity,
                    metadata={"fast_ma": fast_ma, "slow_ma": slow_ma},
                )

            elif crossed_below and has_position:
                qty = position.quantity if position else 0.0
                signal = Signal(
                    symbol=str(self._get_param("symbol", "BTC/USDT")),
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=qty,
                    metadata={"fast_ma": fast_ma, "slow_ma": slow_ma},
                )

        self._prev_fast_ma = fast_ma
        self._prev_slow_ma = slow_ma
        return signal

    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """Not used in bar-based strategy; always returns ``None``."""
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calc_quantity(self, close: float) -> float:
        """Size the position using ATR-based risk."""
        if len(self._closes) < self._atr_period + 1:
            risk_capital = self._capital * self._risk_per_trade_pct
            return risk_capital / close if close > 0 else 0.0

        highs_s = pd.Series(list(self._highs))
        lows_s = pd.Series(list(self._lows))
        closes_s = pd.Series(list(self._closes))
        atr_series = ind.ATR(highs_s, lows_s, closes_s, self._atr_period)
        atr = float(atr_series.iloc[-1])

        if pd.isna(atr) or atr <= 0:
            risk_capital = self._capital * self._risk_per_trade_pct
            return risk_capital / close if close > 0 else 0.0

        risk_capital = self._capital * self._risk_per_trade_pct
        stop_distance = atr * self._atr_multiplier
        return risk_capital / stop_distance if stop_distance > 0 else 0.0
