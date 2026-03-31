"""
Abstract base class for all trading strategies.

Subclasses must implement :meth:`initialize`, :meth:`on_candle`, and
:meth:`on_tick`.  The base class provides position tracking, order helpers,
signal generation, and performance accounting.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import pandas as pd

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


@dataclass
class Signal:
    """A trading signal emitted by a strategy."""

    symbol: str
    signal_type: SignalType
    price: Optional[float]
    quantity: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Tracks an open position for a single symbol."""

    symbol: str
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    def update_price(self, current_price: float) -> None:
        """Recalculate unrealized PnL given the current market price."""
        if self.quantity != 0:
            self.unrealized_pnl = (current_price - self.avg_entry_price) * self.quantity
        else:
            self.unrealized_pnl = 0.0

    @property
    def is_open(self) -> bool:
        return self.quantity != 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.avg_entry_price


@dataclass
class OrderRecord:
    """Minimal order record used for performance tracking."""

    symbol: str
    side: str  # "buy" | "sell"
    quantity: float
    price: float
    timestamp: datetime
    order_id: Optional[str] = None
    commission: float = 0.0
    pnl: float = 0.0


class StrategyBase(ABC):
    """
    Abstract base class for quantitative trading strategies.

    Parameters
    ----------
    name : str
        Human-readable strategy name.
    version : str
        Semantic version string.
    description : str
        Short description of the strategy.
    parameters : dict
        Tunable strategy parameters (hyper-parameters).
    """

    def __init__(
        self,
        name: str = "BaseStrategy",
        version: str = "1.0.0",
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._name = name
        self._version = version
        self._description = description
        self._parameters: Dict[str, Any] = parameters or {}

        self._positions: Dict[str, Position] = {}
        self._orders: List[OrderRecord] = []
        self._signals: List[Signal] = []

        # Capital tracking (set via initialise / backtester injection).
        self._capital: float = 0.0
        self._initial_capital: float = 0.0

        self._initialized = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> Dict[str, Any]:
        return self._parameters

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def initialize(self) -> None:
        """Called once before the strategy starts processing data.

        Use this to set up indicators, warm-up buffers, and any
        state that depends on parameter values.
        """

    @abstractmethod
    def on_candle(self, candle: pd.Series) -> Optional[Signal]:
        """Process a new closed candle.

        Parameters
        ----------
        candle : pd.Series
            Row from an OHLCV DataFrame with index fields
            ``open``, ``high``, ``low``, ``close``, ``volume``.

        Returns
        -------
        Signal or None
        """

    @abstractmethod
    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """Process a real-time tick / order-book update.

        Parameters
        ----------
        tick : dict
            Keys: symbol, price, volume, timestamp.

        Returns
        -------
        Signal or None
        """

    # ------------------------------------------------------------------
    # Order helpers
    # ------------------------------------------------------------------

    def buy(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        commission_rate: float = 0.001,
    ) -> Signal:
        """Generate a buy signal and update position tracking.

        Parameters
        ----------
        symbol : str
        quantity : float
        price : float, optional
            If *None* the signal is treated as a market order.
        commission_rate : float

        Returns
        -------
        Signal
        """
        cost = (price or 0.0) * quantity
        commission = cost * commission_rate

        position = self._positions.setdefault(symbol, Position(symbol=symbol))
        if position.quantity == 0:
            position.avg_entry_price = price or 0.0
            position.quantity = quantity
        else:
            total_qty = position.quantity + quantity
            position.avg_entry_price = (
                position.avg_entry_price * position.quantity + (price or 0.0) * quantity
            ) / total_qty
            position.quantity = total_qty

        self._capital -= cost + commission

        record = OrderRecord(
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=price or 0.0,
            timestamp=datetime.now(timezone.utc),
            commission=commission,
        )
        self._orders.append(record)

        signal = Signal(
            symbol=symbol,
            signal_type=SignalType.BUY,
            price=price,
            quantity=quantity,
        )
        self._signals.append(signal)
        logger.debug("BUY %s qty=%s @ %s", symbol, quantity, price)
        return signal

    def sell(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        commission_rate: float = 0.001,
    ) -> Signal:
        """Generate a sell signal and update position tracking.

        Parameters
        ----------
        symbol : str
        quantity : float
        price : float, optional
        commission_rate : float

        Returns
        -------
        Signal
        """
        proceeds = (price or 0.0) * quantity
        commission = proceeds * commission_rate

        position = self._positions.get(symbol)
        realized = 0.0
        if position and position.is_open:
            realized = (
                (price or position.avg_entry_price) - position.avg_entry_price
            ) * min(quantity, position.quantity)
            position.realized_pnl += realized
            position.quantity = max(0.0, position.quantity - quantity)
            if position.quantity == 0:
                position.avg_entry_price = 0.0

        self._capital += proceeds - commission

        record = OrderRecord(
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=price or 0.0,
            timestamp=datetime.now(timezone.utc),
            commission=commission,
            pnl=realized,
        )
        self._orders.append(record)

        signal = Signal(
            symbol=symbol,
            signal_type=SignalType.SELL,
            price=price,
            quantity=quantity,
        )
        self._signals.append(signal)
        logger.debug("SELL %s qty=%s @ %s  pnl=%s", symbol, quantity, price, realized)
        return signal

    # ------------------------------------------------------------------
    # Position accessors
    # ------------------------------------------------------------------

    def get_position(self, symbol: str) -> Optional[Position]:
        """Return the current position for *symbol*, or ``None``."""
        return self._positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Position]:
        """Return all tracked positions (including flat ones)."""
        return dict(self._positions)

    def get_open_positions(self) -> Dict[str, Position]:
        """Return only positions with non-zero quantity."""
        return {k: v for k, v in self._positions.items() if v.is_open}

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return a summary of strategy performance so far."""
        trades = [o for o in self._orders if o.side == "sell"]
        n = len(trades)
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl < 0]
        total_pnl = sum(t.pnl for t in trades)
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))

        return {
            "total_trades": n,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / n if n else 0.0,
            "total_pnl": total_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": gross_profit / gross_loss if gross_loss else 0.0,
            "current_capital": self._capital,
            "total_return_pct": (
                (self._capital - self._initial_capital) / self._initial_capital * 100
                if self._initial_capital
                else 0.0
            ),
        }

    def get_signals(self) -> List[Signal]:
        """Return all signals emitted during this run."""
        return list(self._signals)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_capital(self, capital: float) -> None:
        """Inject initial capital (called by the backtester / executor)."""
        self._capital = capital
        self._initial_capital = capital

    def _get_param(self, key: str, default: Any = None) -> Any:
        """Retrieve a parameter value with optional default."""
        return self._parameters.get(key, default)
