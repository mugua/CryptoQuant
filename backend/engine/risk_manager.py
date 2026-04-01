"""
Risk management module.

Enforces position size limits, daily loss limits, drawdown limits, and
maximum concurrent open positions.  Provides Kelly criterion position sizing
and risk-adjusted order sizing utilities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """Risk management configuration.

    Parameters
    ----------
    max_position_size_pct : float
        Maximum fraction of portfolio value that a single position may occupy
        (e.g. 0.10 = 10 %).
    max_daily_loss_pct : float
        Maximum fraction of starting-day equity that may be lost before all
        new orders are blocked (e.g. 0.02 = 2 %).
    max_drawdown_limit_pct : float
        Maximum peak-to-trough drawdown fraction before the engine issues a
        force-close (e.g. 0.15 = 15 %).
    max_open_positions : int
        Hard cap on the number of simultaneous open positions.
    """

    max_position_size_pct: float = 0.10
    max_daily_loss_pct: float = 0.02
    max_drawdown_limit_pct: float = 0.15
    max_open_positions: int = 5


@dataclass
class PositionSnapshot:
    symbol: str
    side: str
    quantity: float
    avg_entry_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * (self.current_price or self.avg_entry_price)

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_entry_price) * self.quantity


class RiskManager:
    """
    Stateful risk manager that validates orders before execution.

    Parameters
    ----------
    config : RiskConfig
    initial_equity : float
        Portfolio equity at the start of the session / day.
    """

    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        initial_equity: float = 10_000.0,
    ) -> None:
        self.config = config or RiskConfig()
        self._portfolio_equity: float = initial_equity
        self._peak_equity: float = initial_equity
        self._day_start_equity: float = initial_equity
        self._current_day: date = datetime.now(timezone.utc).date()

        self._positions: Dict[str, PositionSnapshot] = {}
        self._trade_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Order validation
    # ------------------------------------------------------------------

    def check_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
    ) -> Tuple[bool, str]:
        """
        Validate whether an order is permitted under current risk rules.

        Parameters
        ----------
        symbol : str
        side : str
            ``"buy"`` or ``"sell"``.
        quantity : float
        price : float

        Returns
        -------
        (allowed, reason) : tuple[bool, str]
            *allowed* is ``True`` when the order may proceed.
            *reason* is an empty string on success or a human-readable
            explanation of the rejection.
        """
        self._refresh_day()

        order_value = quantity * price

        # --- Max drawdown breach ---
        drawdown = (self._peak_equity - self._portfolio_equity) / self._peak_equity
        if drawdown >= self.config.max_drawdown_limit_pct:
            reason = (
                f"Max drawdown limit breached: current drawdown {drawdown:.2%} >= "
                f"limit {self.config.max_drawdown_limit_pct:.2%}. All new orders blocked."
            )
            logger.warning(reason)
            return False, reason

        # --- Daily loss limit ---
        daily_loss = (self._day_start_equity - self._portfolio_equity) / self._day_start_equity
        if daily_loss >= self.config.max_daily_loss_pct:
            reason = (
                f"Daily loss limit breached: {daily_loss:.2%} >= "
                f"limit {self.config.max_daily_loss_pct:.2%}. No new orders today."
            )
            logger.warning(reason)
            return False, reason

        # --- Position size limit (applies to buy orders) ---
        if side.lower() == "buy":
            pct = order_value / self._portfolio_equity if self._portfolio_equity else 1.0
            if pct > self.config.max_position_size_pct:
                reason = (
                    f"Order value {order_value:.2f} ({pct:.2%} of equity) exceeds "
                    f"max position size {self.config.max_position_size_pct:.2%}."
                )
                logger.warning(reason)
                return False, reason

            # --- Max open positions ---
            open_positions = sum(1 for p in self._positions.values() if p.quantity > 0)
            if symbol not in self._positions and open_positions >= self.config.max_open_positions:
                reason = (
                    f"Max open positions ({self.config.max_open_positions}) reached. "
                    f"Cannot open new position for {symbol}."
                )
                logger.warning(reason)
                return False, reason

        return True, ""

    # ------------------------------------------------------------------
    # Position updates
    # ------------------------------------------------------------------

    def update_positions(self, trade: Dict[str, Any]) -> None:
        """
        Update internal position state after a fill.

        Parameters
        ----------
        trade : dict
            Expected keys: ``symbol``, ``side``, ``quantity``, ``price``,
            ``timestamp`` (optional).
        """
        symbol = trade["symbol"]
        side = trade["side"].lower()
        qty = float(trade["quantity"])
        price = float(trade["price"])
        commission = float(trade.get("commission", 0.0))

        if side == "buy":
            if symbol in self._positions:
                pos = self._positions[symbol]
                total_qty = pos.quantity + qty
                pos.avg_entry_price = (
                    pos.avg_entry_price * pos.quantity + price * qty
                ) / total_qty
                pos.quantity = total_qty
            else:
                self._positions[symbol] = PositionSnapshot(
                    symbol=symbol,
                    side="long",
                    quantity=qty,
                    avg_entry_price=price,
                    current_price=price,
                )
            self._portfolio_equity -= qty * price + commission

        elif side == "sell":
            pos = self._positions.get(symbol)
            if pos:
                pnl = (price - pos.avg_entry_price) * min(qty, pos.quantity) - commission
                pos.quantity = max(0.0, pos.quantity - qty)
                if pos.quantity == 0:
                    pos.avg_entry_price = 0.0
                self._portfolio_equity += qty * price - commission
            else:
                self._portfolio_equity += qty * price - commission

        # Update peak equity for drawdown tracking.
        if self._portfolio_equity > self._peak_equity:
            self._peak_equity = self._portfolio_equity

        self._trade_log.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": qty,
                "price": price,
                "commission": commission,
                "equity_after": self._portfolio_equity,
                "timestamp": trade.get("timestamp", datetime.now(timezone.utc)),
            }
        )
        logger.debug(
            "Position update %s %s qty=%.4f @ %.2f  equity=%.2f",
            side, symbol, qty, price, self._portfolio_equity,
        )

    def update_market_prices(self, prices: Dict[str, float]) -> None:
        """Refresh current market prices for mark-to-market calculations."""
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].current_price = price

    def force_close_all(self) -> List[Dict[str, Any]]:
        """
        Return close-order specs for all open positions (called on limit breach).

        Returns
        -------
        list of dict
            Each dict has keys: symbol, side, quantity.
        """
        orders = []
        for symbol, pos in self._positions.items():
            if pos.quantity > 0:
                orders.append(
                    {"symbol": symbol, "side": "sell", "quantity": pos.quantity}
                )
        logger.warning("Force-close triggered. %d positions to close.", len(orders))
        return orders

    # ------------------------------------------------------------------
    # Risk metrics
    # ------------------------------------------------------------------

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Return current risk metrics snapshot."""
        self._refresh_day()
        drawdown = (self._peak_equity - self._portfolio_equity) / self._peak_equity
        daily_loss = (self._day_start_equity - self._portfolio_equity) / self._day_start_equity
        open_positions = sum(1 for p in self._positions.values() if p.quantity > 0)
        total_exposure = sum(
            p.market_value for p in self._positions.values() if p.quantity > 0
        )
        return {
            "portfolio_equity": self._portfolio_equity,
            "peak_equity": self._peak_equity,
            "current_drawdown_pct": drawdown * 100,
            "daily_loss_pct": daily_loss * 100,
            "open_positions": open_positions,
            "total_exposure": total_exposure,
            "exposure_pct": total_exposure / self._portfolio_equity * 100 if self._portfolio_equity else 0.0,
            "max_position_size_pct": self.config.max_position_size_pct * 100,
            "max_daily_loss_pct": self.config.max_daily_loss_pct * 100,
            "max_drawdown_limit_pct": self.config.max_drawdown_limit_pct * 100,
            "max_open_positions": self.config.max_open_positions,
        }

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def kelly_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.25,
    ) -> float:
        """
        Kelly criterion position size as a fraction of equity.

        Parameters
        ----------
        win_rate : float
            Historical win rate (0–1).
        avg_win : float
            Average winning trade return (positive fraction, e.g. 0.05 = 5 %).
        avg_loss : float
            Average losing trade return (positive magnitude, e.g. 0.03 = 3 %).
        fraction : float
            Kelly fraction (default 0.25 = quarter-Kelly for safety).

        Returns
        -------
        float
            Suggested position size as a fraction of portfolio equity.
        """
        if avg_loss <= 0:
            return 0.0
        b = avg_win / avg_loss
        p = win_rate
        q = 1.0 - win_rate
        kelly = (b * p - q) / b
        return max(0.0, min(kelly * fraction, self.config.max_position_size_pct))

    def risk_adjusted_quantity(
        self,
        symbol: str,
        price: float,
        risk_per_trade_pct: float = 0.01,
        stop_loss_pct: float = 0.02,
    ) -> float:
        """
        Calculate order quantity based on a fixed fractional risk model.

        Parameters
        ----------
        symbol : str
        price : float
            Current asset price.
        risk_per_trade_pct : float
            Fraction of equity risked per trade (default 1 %).
        stop_loss_pct : float
            Assumed stop-loss distance as fraction of price (default 2 %).

        Returns
        -------
        float
            Suggested quantity to buy.
        """
        if price <= 0 or stop_loss_pct <= 0:
            return 0.0
        risk_amount = self._portfolio_equity * risk_per_trade_pct
        qty = risk_amount / (price * stop_loss_pct)
        # Cap at max_position_size.
        max_qty = (self._portfolio_equity * self.config.max_position_size_pct) / price
        return min(qty, max_qty)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_day(self) -> None:
        """Reset daily metrics at the start of a new calendar day (UTC)."""
        today = datetime.now(timezone.utc).date()
        if today != self._current_day:
            self._current_day = today
            self._day_start_equity = self._portfolio_equity
            logger.info("New trading day %s. Day-start equity reset to %.2f", today, self._portfolio_equity)
