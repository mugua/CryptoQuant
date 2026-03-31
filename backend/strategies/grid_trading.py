"""
Grid trading strategy.

Creates a static price grid between *lower_price* and *upper_price* and
manages buy/sell orders at each grid level.  Each buy at a grid level
creates a corresponding sell order one level above.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from engine.strategy_base import Signal, SignalType, StrategyBase


class GridTradingStrategy(StrategyBase):
    """
    Grid trading strategy.

    Parameters
    ----------
    grid_count : int
        Number of grid levels (default 10).
    upper_price : float
        Upper boundary of the grid.
    lower_price : float
        Lower boundary of the grid.
    investment_per_grid : float
        USDT amount to invest per grid level.
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="GridTradingStrategy",
            version="1.0.0",
            description="Static price grid with automated buy/sell order management.",
            parameters=parameters or {},
        )
        self._grid_count: int = int(self._get_param("grid_count", 10))
        self._upper_price: float = float(self._get_param("upper_price", 0))
        self._lower_price: float = float(self._get_param("lower_price", 0))
        self._investment_per_grid: float = float(self._get_param("investment_per_grid", 100.0))

        # Grid levels and state.
        self._grid_levels: List[float] = []
        # Maps grid level index → {"bought": bool, "sell_above": float, "qty": float}
        self._grid_state: Dict[int, Dict[str, Any]] = {}
        self._total_profit: float = 0.0
        self._initialized_grid: bool = False

    def initialize(self) -> None:
        """Build the grid and reset state."""
        self._grid_state = {}
        self._total_profit = 0.0
        self._initialized_grid = False

        if self._upper_price > self._lower_price and self._grid_count >= 2:
            step = (self._upper_price - self._lower_price) / self._grid_count
            self._grid_levels = [
                round(self._lower_price + i * step, 8)
                for i in range(self._grid_count + 1)
            ]
            for i, level in enumerate(self._grid_levels):
                self._grid_state[i] = {
                    "level": level,
                    "bought": False,
                    "sell_target": self._grid_levels[i + 1] if i + 1 < len(self._grid_levels) else None,
                    "qty": 0.0,
                }

    def on_candle(self, candle: pd.Series) -> Optional[Signal]:
        """
        Scan all grid levels against the current close price.

        Generates a buy signal when the price is at or below a grid buy level
        that has not been filled, and a sell signal when the price is at or
        above the sell target for an active grid position.

        Parameters
        ----------
        candle : pd.Series

        Returns
        -------
        Signal or None
            Returns the first triggered grid signal.
        """
        if not self._grid_levels:
            return None

        close = float(candle["close"])
        symbol = str(self._get_param("symbol", "BTC/USDT"))

        # Out of grid range – no action.
        if close < self._lower_price or close > self._upper_price:
            return None

        # Check sell signals first (take profit has priority).
        for i, state in self._grid_state.items():
            if state["bought"] and state["sell_target"] is not None:
                if close >= state["sell_target"]:
                    qty = state["qty"]
                    profit = (close - state["level"]) * qty
                    self._total_profit += profit
                    state["bought"] = False
                    state["qty"] = 0.0
                    return Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=close,
                        quantity=qty,
                        metadata={
                            "grid_level": state["level"],
                            "sell_target": state["sell_target"],
                            "grid_profit": profit,
                            "total_grid_profit": self._total_profit,
                        },
                    )

        # Check buy signals.
        for i, state in self._grid_state.items():
            if not state["bought"]:
                if close <= state["level"]:
                    qty = self._investment_per_grid / close if close > 0 else 0.0
                    if qty <= 0:
                        continue
                    state["bought"] = True
                    state["qty"] = qty
                    return Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=close,
                        quantity=qty,
                        metadata={
                            "grid_level": state["level"],
                            "sell_target": state["sell_target"],
                        },
                    )

        return None

    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """Not used in bar-based strategy."""
        return None

    # ------------------------------------------------------------------
    # Grid analytics
    # ------------------------------------------------------------------

    def get_grid_state(self) -> List[Dict[str, Any]]:
        """Return the current state of all grid levels."""
        return [
            {
                "index": i,
                "level": state["level"],
                "bought": state["bought"],
                "sell_target": state["sell_target"],
                "quantity": state["qty"],
            }
            for i, state in self._grid_state.items()
        ]

    def get_grid_profit(self) -> float:
        """Return cumulative realised profit from grid trades."""
        return self._total_profit

    def get_open_grid_positions(self) -> int:
        """Return the number of filled (holding) grid levels."""
        return sum(1 for s in self._grid_state.values() if s["bought"])
