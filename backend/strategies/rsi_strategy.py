"""
RSI mean-reversion strategy.

Buys when RSI is oversold, sells when RSI is overbought.
Exits existing positions on RSI midline cross.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, Optional

import pandas as pd

from engine.strategy_base import Signal, SignalType, StrategyBase
from engine import indicators as ind


class RSIStrategy(StrategyBase):
    """
    RSI-driven mean-reversion strategy.

    Parameters
    ----------
    rsi_period : int
        RSI look-back period (default 14).
    oversold : float
        RSI level at which a buy signal is triggered (default 30).
    overbought : float
        RSI level at which a sell signal is triggered (default 70).
    exit_rsi_buy : float
        RSI level that closes a long position from above (midline, default 50).
    exit_rsi_sell : float
        RSI level that closes a short position from below (midline, default 50).
    risk_per_trade_pct : float
        Fraction of capital to deploy per trade (default 0.95).
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="RSIStrategy",
            version="1.0.0",
            description="Buy oversold, sell overbought; exit on RSI midline cross.",
            parameters=parameters or {},
        )
        self._rsi_period: int = int(self._get_param("rsi_period", 14))
        self._oversold: float = float(self._get_param("oversold", 30))
        self._overbought: float = float(self._get_param("overbought", 70))
        self._exit_rsi_buy: float = float(self._get_param("exit_rsi_buy", 50))
        self._exit_rsi_sell: float = float(self._get_param("exit_rsi_sell", 50))
        self._risk_pct: float = float(self._get_param("risk_per_trade_pct", 0.95))

        buf_size = self._rsi_period * 3 + 10
        self._closes: Deque[float] = deque(maxlen=buf_size)
        self._prev_rsi: Optional[float] = None

    def initialize(self) -> None:
        """Reset warm-up buffer."""
        self._closes.clear()
        self._prev_rsi = None

    def on_candle(self, candle: pd.Series) -> Optional[Signal]:
        """
        Evaluate RSI and generate entry/exit signals.

        Parameters
        ----------
        candle : pd.Series

        Returns
        -------
        Signal or None
        """
        self._closes.append(float(candle["close"]))

        if len(self._closes) < self._rsi_period + 1:
            return None

        closes_s = pd.Series(list(self._closes))
        rsi_series = ind.RSI(closes_s, self._rsi_period)
        rsi = float(rsi_series.iloc[-1])

        if pd.isna(rsi):
            self._prev_rsi = rsi
            return None

        close = float(candle["close"])
        symbol = str(self._get_param("symbol", "BTC/USDT"))
        position = self.get_position(symbol)
        has_position = position is not None and position.is_open
        signal: Optional[Signal] = None

        if not has_position:
            if rsi < self._oversold:
                qty = self._calc_quantity(close)
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=qty,
                    metadata={"rsi": rsi},
                )
        else:
            # Exit long: RSI is overbought OR RSI crosses above exit threshold.
            exit_on_overbought = rsi > self._overbought
            midline_exit = (
                self._prev_rsi is not None
                and self._prev_rsi < self._exit_rsi_buy
                and rsi >= self._exit_rsi_buy
            )
            if exit_on_overbought or midline_exit:
                qty = position.quantity if position else 0.0
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=qty,
                    metadata={"rsi": rsi, "exit_reason": "overbought" if exit_on_overbought else "midline"},
                )

        self._prev_rsi = rsi
        return signal

    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """Not used in bar-based strategy."""
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calc_quantity(self, close: float) -> float:
        """Allocate *risk_pct* of available capital."""
        if close <= 0:
            return 0.0
        return (self._capital * self._risk_pct) / close
