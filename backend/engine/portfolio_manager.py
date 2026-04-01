"""
Portfolio manager – tracks positions across multiple exchanges, calculates
total value, PnL, and performance metrics in USDT.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PositionEntry:
    """A single position held on one exchange."""

    exchange: str
    symbol: str
    base_asset: str
    quote_asset: str
    quantity: float
    avg_entry_price: float
    current_price: float = 0.0
    realized_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_entry_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis * 100


@dataclass
class PortfolioSnapshot:
    """Point-in-time portfolio summary."""

    timestamp: datetime
    total_value_usdt: float
    cash_usdt: float
    positions_value_usdt: float
    unrealized_pnl: float
    realized_pnl: float
    total_return_pct: float


class PortfolioManager:
    """
    Tracks positions across multiple exchanges and provides aggregated PnL,
    rebalancing helpers, and performance metrics.

    Parameters
    ----------
    initial_cash : float
        Starting USDT cash balance.
    """

    def __init__(self, initial_cash: float = 10_000.0) -> None:
        self._initial_cash = initial_cash
        self._cash: float = initial_cash
        self._positions: Dict[str, PositionEntry] = {}  # key = "exchange:symbol"
        self._snapshots: List[PortfolioSnapshot] = []
        self._realized_pnl: float = 0.0
        self._commission_paid: float = 0.0

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def add_position(
        self,
        exchange: str,
        symbol: str,
        quantity: float,
        price: float,
        commission: float = 0.0,
    ) -> PositionEntry:
        """
        Record a buy fill that opens or increases a position.

        Parameters
        ----------
        exchange : str
        symbol : str
            Trading pair, e.g. ``"BTC/USDT"``.
        quantity : float
        price : float
            Fill price.
        commission : float

        Returns
        -------
        PositionEntry
        """
        key = f"{exchange}:{symbol}"
        parts = symbol.split("/")
        base = parts[0] if parts else symbol
        quote = parts[1] if len(parts) > 1 else "USDT"
        cost = quantity * price + commission
        self._cash -= cost
        self._commission_paid += commission

        if key in self._positions:
            pos = self._positions[key]
            total_qty = pos.quantity + quantity
            pos.avg_entry_price = (pos.avg_entry_price * pos.quantity + price * quantity) / total_qty
            pos.quantity = total_qty
            pos.current_price = price
        else:
            self._positions[key] = PositionEntry(
                exchange=exchange,
                symbol=symbol,
                base_asset=base,
                quote_asset=quote,
                quantity=quantity,
                avg_entry_price=price,
                current_price=price,
            )

        logger.debug("Added position %s qty=%.6f @ %.2f", key, quantity, price)
        return self._positions[key]

    def reduce_position(
        self,
        exchange: str,
        symbol: str,
        quantity: float,
        price: float,
        commission: float = 0.0,
    ) -> Tuple[float, float]:
        """
        Record a sell fill that reduces or closes a position.

        Parameters
        ----------
        exchange : str
        symbol : str
        quantity : float
        price : float
        commission : float

        Returns
        -------
        (realized_pnl, remaining_quantity) : tuple[float, float]
        """
        key = f"{exchange}:{symbol}"
        proceeds = quantity * price - commission
        self._cash += proceeds
        self._commission_paid += commission

        pos = self._positions.get(key)
        if pos is None:
            logger.warning("Reducing non-existent position %s", key)
            return 0.0, 0.0

        sell_qty = min(quantity, pos.quantity)
        pnl = (price - pos.avg_entry_price) * sell_qty - commission
        pos.realized_pnl += pnl
        self._realized_pnl += pnl
        pos.quantity -= sell_qty
        pos.current_price = price

        if pos.quantity <= 0:
            del self._positions[key]
            logger.debug("Position closed %s  realized_pnl=%.2f", key, pnl)
        else:
            logger.debug("Reduced position %s to qty=%.6f  pnl=%.2f", key, pos.quantity, pnl)

        return pnl, pos.quantity if key in self._positions else 0.0

    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        Update current market prices for mark-to-market.

        Parameters
        ----------
        prices : dict
            Mapping of symbol → current USDT price.
        """
        for key, pos in self._positions.items():
            price = prices.get(pos.symbol) or prices.get(key)
            if price is not None:
                pos.current_price = price

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------

    def get_total_value(self) -> float:
        """Return total portfolio value in USDT (cash + positions mark-to-market)."""
        positions_value = sum(p.market_value for p in self._positions.values())
        return self._cash + positions_value

    def get_unrealized_pnl(self) -> float:
        """Return total unrealized PnL across all open positions."""
        return sum(p.unrealized_pnl for p in self._positions.values())

    def get_realized_pnl(self) -> float:
        """Return cumulative realized PnL since portfolio inception."""
        return self._realized_pnl

    def get_position(self, exchange: str, symbol: str) -> Optional[PositionEntry]:
        """Return the PositionEntry for (exchange, symbol) or ``None``."""
        return self._positions.get(f"{exchange}:{symbol}")

    def get_all_positions(self) -> List[PositionEntry]:
        """Return all open positions."""
        return list(self._positions.values())

    def get_position_weight(self, exchange: str, symbol: str) -> float:
        """Return position weight as a fraction of total portfolio value."""
        total = self.get_total_value()
        if total == 0:
            return 0.0
        pos = self.get_position(exchange, symbol)
        return pos.market_value / total if pos else 0.0

    # ------------------------------------------------------------------
    # Rebalancing
    # ------------------------------------------------------------------

    def get_rebalance_orders(
        self, target_weights: Dict[str, float], prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Compute the orders needed to rebalance to *target_weights*.

        Parameters
        ----------
        target_weights : dict
            Mapping of ``"exchange:symbol"`` → desired weight (0–1).
            Weights should sum to ≤ 1 (remainder stays as cash).
        prices : dict
            Mapping of symbol → current price.

        Returns
        -------
        list of dict
            Each order has keys: exchange, symbol, side, quantity, price.
        """
        self.update_prices(prices)
        total_value = self.get_total_value()
        orders = []

        for key, target_weight in target_weights.items():
            exchange, symbol = key.split(":", 1)
            price = prices.get(symbol, 0.0)
            if price <= 0:
                continue

            target_value = total_value * target_weight
            current_value = 0.0
            pos = self._positions.get(key)
            if pos:
                current_value = pos.market_value

            delta_value = target_value - current_value
            quantity = abs(delta_value) / price

            if delta_value > 0:
                orders.append({"exchange": exchange, "symbol": symbol, "side": "buy", "quantity": quantity, "price": price})
            elif delta_value < -1.0:
                orders.append({"exchange": exchange, "symbol": symbol, "side": "sell", "quantity": quantity, "price": price})

        return orders

    # ------------------------------------------------------------------
    # Performance metrics
    # ------------------------------------------------------------------

    def take_snapshot(self) -> PortfolioSnapshot:
        """Record and return the current portfolio snapshot."""
        total = self.get_total_value()
        unrealized = self.get_unrealized_pnl()
        total_return = (total - self._initial_cash) / self._initial_cash * 100 if self._initial_cash else 0.0

        snap = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value_usdt=total,
            cash_usdt=self._cash,
            positions_value_usdt=total - self._cash,
            unrealized_pnl=unrealized,
            realized_pnl=self._realized_pnl,
            total_return_pct=total_return,
        )
        self._snapshots.append(snap)
        return snap

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Compute portfolio-level performance metrics from snapshot history."""
        if len(self._snapshots) < 2:
            self.take_snapshot()

        values = [s.total_value_usdt for s in self._snapshots]
        total = self.get_total_value()
        total_return = (total - self._initial_cash) / self._initial_cash * 100

        # Max drawdown.
        peak = self._initial_cash
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

        # Approximate Sharpe from snapshots.
        returns = [
            (values[i] - values[i - 1]) / values[i - 1]
            for i in range(1, len(values))
        ]
        sharpe = 0.0
        if len(returns) > 1:
            mean_r = sum(returns) / len(returns)
            std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1))
            sharpe = (mean_r / std_r * math.sqrt(252)) if std_r > 0 else 0.0

        return {
            "initial_cash": self._initial_cash,
            "current_value": total,
            "cash": self._cash,
            "unrealized_pnl": self.get_unrealized_pnl(),
            "realized_pnl": self._realized_pnl,
            "total_return_pct": total_return,
            "max_drawdown_pct": max_dd * 100,
            "sharpe_ratio": sharpe,
            "commission_paid": self._commission_paid,
            "open_positions": len(self._positions),
        }

    def get_position_sizing(
        self,
        exchange: str,
        symbol: str,
        price: float,
        risk_pct: float = 0.01,
        stop_loss_pct: float = 0.02,
    ) -> float:
        """
        Suggest a position size using fixed fractional risk.

        Parameters
        ----------
        exchange : str
        symbol : str
        price : float
        risk_pct : float
            Fraction of portfolio to risk per trade.
        stop_loss_pct : float
            Assumed stop-loss distance as fraction of price.

        Returns
        -------
        float
            Suggested quantity.
        """
        total = self.get_total_value()
        risk_amount = total * risk_pct
        if price <= 0 or stop_loss_pct <= 0:
            return 0.0
        return risk_amount / (price * stop_loss_pct)
