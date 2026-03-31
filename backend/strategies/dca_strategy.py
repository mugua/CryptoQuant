"""
Dollar-Cost Averaging (DCA) strategy.

Buys a fixed USDT amount at regular intervals, with an extra buy triggered
on significant price drops and a take-profit exit when the target gain is reached.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from engine.strategy_base import Signal, SignalType, StrategyBase


class DCAStrategy(StrategyBase):
    """
    Dollar-Cost Averaging strategy.

    Parameters
    ----------
    investment_amount : float
        USDT amount to invest on each scheduled buy (default 100).
    interval_days : int
        Days between regular buys (default 7).
    max_positions : int
        Maximum number of accumulated DCA entries (default 10).
    take_profit_pct : float
        Percentage gain above average entry price that triggers a full exit
        (default 20 %).
    drop_trigger_pct : float
        Price drop percentage relative to last buy price that triggers an
        extra buy (negative value, default -5 %).
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="DCAStrategy",
            version="1.0.0",
            description="Regular interval DCA with drop-triggered extra buys and take-profit.",
            parameters=parameters or {},
        )
        self._investment_amount: float = float(self._get_param("investment_amount", 100.0))
        self._interval_days: int = int(self._get_param("interval_days", 7))
        self._max_positions: int = int(self._get_param("max_positions", 10))
        self._take_profit_pct: float = float(self._get_param("take_profit_pct", 20.0))
        self._drop_trigger_pct: float = float(self._get_param("drop_trigger_pct", -5.0))

        # Internal state.
        self._last_buy_time: Optional[datetime] = None
        self._last_buy_price: Optional[float] = None
        self._entries: List[Dict[str, Any]] = []  # [{price, qty, time}]
        self._total_invested: float = 0.0

    def initialize(self) -> None:
        """Reset state."""
        self._last_buy_time = None
        self._last_buy_price = None
        self._entries = []
        self._total_invested = 0.0

    @property
    def _entry_count(self) -> int:
        return len(self._entries)

    @property
    def _avg_entry_price(self) -> float:
        if not self._entries:
            return 0.0
        total_qty = sum(e["qty"] for e in self._entries)
        if total_qty == 0:
            return 0.0
        return sum(e["price"] * e["qty"] for e in self._entries) / total_qty

    @property
    def _total_qty(self) -> float:
        return sum(e["qty"] for e in self._entries)

    def on_candle(self, candle: pd.Series) -> Optional[Signal]:
        """
        Evaluate DCA buy and take-profit conditions.

        Parameters
        ----------
        candle : pd.Series

        Returns
        -------
        Signal or None
        """
        close = float(candle["close"])
        symbol = str(self._get_param("symbol", "BTC/USDT"))

        # Determine candle timestamp.
        ts = candle.name if isinstance(candle.name, datetime) else datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        signal: Optional[Signal] = None

        # --- Take-profit check ---
        if self._entry_count > 0 and self._total_qty > 0:
            avg = self._avg_entry_price
            if avg > 0:
                gain_pct = (close - avg) / avg * 100
                if gain_pct >= self._take_profit_pct:
                    qty = self._total_qty
                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=close,
                        quantity=qty,
                        metadata={
                            "reason": "take_profit",
                            "gain_pct": gain_pct,
                            "avg_entry": avg,
                            "entries": self._entry_count,
                        },
                    )
                    self._entries = []
                    self._total_invested = 0.0
                    self._last_buy_price = None
                    self._last_buy_time = None
                    return signal

        # --- Regular interval buy ---
        interval_elapsed = (
            self._last_buy_time is None
            or (ts - self._last_buy_time) >= timedelta(days=self._interval_days)
        )
        if interval_elapsed and self._entry_count < self._max_positions:
            qty = self._investment_amount / close if close > 0 else 0.0
            if qty > 0:
                self._entries.append({"price": close, "qty": qty, "time": ts})
                self._total_invested += self._investment_amount
                self._last_buy_time = ts
                self._last_buy_price = close
                return Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=qty,
                    metadata={
                        "reason": "scheduled",
                        "entry_number": self._entry_count,
                        "total_invested": self._total_invested,
                    },
                )

        # --- Extra buy on significant drop ---
        if (
            self._last_buy_price is not None
            and self._entry_count < self._max_positions
            and signal is None
        ):
            drop_pct = (close - self._last_buy_price) / self._last_buy_price * 100
            if drop_pct <= self._drop_trigger_pct:
                qty = self._investment_amount / close if close > 0 else 0.0
                if qty > 0:
                    self._entries.append({"price": close, "qty": qty, "time": ts})
                    self._total_invested += self._investment_amount
                    self._last_buy_price = close
                    return Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=close,
                        quantity=qty,
                        metadata={
                            "reason": "drop_trigger",
                            "drop_pct": drop_pct,
                            "entry_number": self._entry_count,
                            "total_invested": self._total_invested,
                        },
                    )

        return signal

    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """Not used in bar-based strategy."""
        return None

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_dca_summary(self) -> Dict[str, Any]:
        """Return a snapshot of the DCA state."""
        return {
            "entry_count": self._entry_count,
            "total_qty": self._total_qty,
            "avg_entry_price": self._avg_entry_price,
            "total_invested": self._total_invested,
            "last_buy_time": self._last_buy_time,
            "last_buy_price": self._last_buy_price,
        }
