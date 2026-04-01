"""
Bollinger Bands mean-reversion strategy.

Enters long on lower-band touches during a squeeze; exits on upper-band
touch or stop-loss at the middle band.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, Optional

import pandas as pd

from engine.strategy_base import Signal, SignalType, StrategyBase
from engine import indicators as ind


class BollingerBandsStrategy(StrategyBase):
    """
    Bollinger Bands mean-reversion strategy.

    Parameters
    ----------
    period : int
        Rolling window for the middle band SMA (default 20).
    std_dev : float
        Number of standard deviations for the bands (default 2.0).
    squeeze_threshold : float
        Band-width / middle-band ratio below which a "squeeze" is declared
        (default 0.1 = 10 %).  Entries are only taken during squeezes.
    risk_per_trade_pct : float
        Fraction of capital deployed per trade (default 0.95).
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="BollingerBandsStrategy",
            version="1.0.0",
            description="Mean reversion on lower-band touch with squeeze filter.",
            parameters=parameters or {},
        )
        self._period: int = int(self._get_param("period", 20))
        self._std_dev: float = float(self._get_param("std_dev", 2.0))
        self._squeeze_threshold: float = float(self._get_param("squeeze_threshold", 0.1))
        self._risk_pct: float = float(self._get_param("risk_per_trade_pct", 0.95))

        buf_size = self._period * 3 + 10
        self._closes: Deque[float] = deque(maxlen=buf_size)
        self._stop_loss_price: Optional[float] = None

    def initialize(self) -> None:
        """Reset buffers."""
        self._closes.clear()
        self._stop_loss_price = None

    def on_candle(self, candle: pd.Series) -> Optional[Signal]:
        """
        Evaluate Bollinger Band conditions and return a signal.

        Parameters
        ----------
        candle : pd.Series

        Returns
        -------
        Signal or None
        """
        self._closes.append(float(candle["close"]))

        if len(self._closes) < self._period:
            return None

        closes_s = pd.Series(list(self._closes))
        upper, middle, lower = ind.BollingerBands(closes_s, self._period, self._std_dev)

        ub = float(upper.iloc[-1])
        mb = float(middle.iloc[-1])
        lb = float(lower.iloc[-1])

        if pd.isna(ub) or pd.isna(mb) or pd.isna(lb):
            return None

        close = float(candle["close"])
        symbol = str(self._get_param("symbol", "BTC/USDT"))
        position = self.get_position(symbol)
        has_position = position is not None and position.is_open
        signal: Optional[Signal] = None

        # Squeeze detection: band width relative to middle band.
        band_width = (ub - lb) / mb if mb != 0 else 1.0
        in_squeeze = band_width < self._squeeze_threshold

        if not has_position:
            # Entry: price touches or breaches the lower band during a squeeze.
            if close <= lb and in_squeeze:
                qty = self._calc_quantity(close)
                self._stop_loss_price = mb  # Stop at middle band.
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=qty,
                    metadata={"lower_band": lb, "middle_band": mb, "upper_band": ub, "band_width": band_width},
                )
        else:
            qty = position.quantity if position else 0.0
            exit_triggered = False
            exit_reason = ""

            # Exit: price touches upper band.
            if close >= ub:
                exit_triggered = True
                exit_reason = "upper_band_touch"

            # Stop-loss: price falls below middle band.
            elif self._stop_loss_price is not None and close < self._stop_loss_price:
                exit_triggered = True
                exit_reason = "stop_loss_midline"

            if exit_triggered:
                self._stop_loss_price = None
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=qty,
                    metadata={
                        "lower_band": lb,
                        "middle_band": mb,
                        "upper_band": ub,
                        "exit_reason": exit_reason,
                    },
                )

        return signal

    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """Not used in bar-based strategy."""
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calc_quantity(self, close: float) -> float:
        if close <= 0:
            return 0.0
        return (self._capital * self._risk_pct) / close
