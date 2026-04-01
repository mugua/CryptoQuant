"""
Execution engine – places and manages orders on a live exchange via ccxt.

Features
--------
* Market and limit orders with retry logic.
* Order state machine (pending → open → filled / cancelled / failed).
* Graceful error handling with exponential back-off.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import ccxt

logger = logging.getLogger(__name__)

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 0.5


class OrderState(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class OrderRecord:
    """Tracks a single order through its lifecycle."""

    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    state: OrderState = OrderState.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw: Dict[str, Any] = field(default_factory=dict)


class ExecutionError(Exception):
    """Raised when the execution engine encounters a non-retriable error."""


class ExecutionEngine:
    """
    Thin wrapper around a ccxt exchange that provides order placement,
    cancellation, status polling, and a local order registry.

    Parameters
    ----------
    exchange_id : str
        ccxt exchange identifier.
    api_key : str, optional
    api_secret : str, optional
    sandbox : bool
        Use exchange testnet when available.
    retry_attempts : int
    retry_delay : float
        Base delay for exponential back-off.
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        self.exchange_id = exchange_id
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self._sandbox = sandbox
        self._exchange: Optional[ccxt.Exchange] = None
        self._orders: Dict[str, OrderRecord] = {}

        config: Dict[str, Any] = {"enableRateLimit": True}
        if api_key:
            config["apiKey"] = api_key
        if api_secret:
            config["secret"] = api_secret
        self._exchange_config = config

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Instantiate and connect to the exchange."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
        except AttributeError as exc:
            raise ExecutionError(f"Unknown exchange: {self.exchange_id}") from exc
        self._exchange = exchange_class(self._exchange_config)
        if self._sandbox and self._exchange.urls.get("test"):
            self._exchange.set_sandbox_mode(True)
        self._retry(self._exchange.load_markets)
        name = str(self.exchange_id)
        logger.info("ExecutionEngine connected to %s (sandbox=%s)", name, self._sandbox)

    def disconnect(self) -> None:
        """Close the exchange connection."""
        if self._exchange and hasattr(self._exchange, "close"):
            try:
                self._exchange.close()
            except Exception:
                pass
        self._exchange = None

    @property
    def exchange(self) -> ccxt.Exchange:
        if self._exchange is None:
            raise ExecutionError("Not connected. Call connect() first.")
        return self._exchange

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        params: Optional[Dict[str, Any]] = None,
    ) -> OrderRecord:
        """
        Submit a market order.

        Parameters
        ----------
        symbol : str
        side : str
            ``"buy"`` or ``"sell"``.
        quantity : float
        params : dict, optional
            Extra ccxt params forwarded to the exchange.

        Returns
        -------
        OrderRecord
        """
        params = params or {}
        raw = self._retry(
            self.exchange.create_market_order, symbol, side, quantity, None, params
        )
        record = self._record_from_raw(raw, "market", quantity, price=None)
        self._orders[record.order_id] = record
        logger.info("Market order placed: %s %s %s qty=%.6f id=%s", side, quantity, symbol, quantity, record.order_id)
        return record

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        params: Optional[Dict[str, Any]] = None,
    ) -> OrderRecord:
        """
        Submit a limit order.

        Parameters
        ----------
        symbol : str
        side : str
        quantity : float
        price : float
        params : dict, optional

        Returns
        -------
        OrderRecord
        """
        params = params or {}
        raw = self._retry(
            self.exchange.create_limit_order, symbol, side, quantity, price, params
        )
        record = self._record_from_raw(raw, "limit", quantity, price=price)
        self._orders[record.order_id] = record
        logger.info("Limit order placed: %s %s qty=%.6f @ %.4f id=%s", side, symbol, quantity, price, record.order_id)
        return record

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an open order.

        Parameters
        ----------
        order_id : str
        symbol : str, optional
            Required by some exchanges.

        Returns
        -------
        bool
            ``True`` on success.
        """
        try:
            self._retry(self.exchange.cancel_order, order_id, symbol)
            if order_id in self._orders:
                self._orders[order_id].state = OrderState.CANCELLED
                self._orders[order_id].updated_at = datetime.now(timezone.utc)
            logger.info("Order cancelled: %s", order_id)
            return True
        except ccxt.OrderNotFound:
            logger.warning("Cancel failed – order not found: %s", order_id)
            return False

    def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> OrderRecord:
        """
        Fetch the current status of an order from the exchange.

        Parameters
        ----------
        order_id : str
        symbol : str, optional

        Returns
        -------
        OrderRecord
        """
        raw = self._retry(self.exchange.fetch_order, order_id, symbol)
        record = self._update_record_from_raw(order_id, raw)
        return record

    def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderRecord]:
        """
        Return all currently open orders.

        Parameters
        ----------
        symbol : str, optional
            Filter by symbol when provided.

        Returns
        -------
        list of OrderRecord
        """
        raw_list = self._retry(self.exchange.fetch_open_orders, symbol)
        records = []
        for raw in raw_list:
            oid = str(raw.get("id", ""))
            record = self._update_record_from_raw(oid, raw)
            records.append(record)
        return records

    def get_local_orders(self) -> Dict[str, OrderRecord]:
        """Return the local order registry (all orders placed this session)."""
        return dict(self._orders)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _record_from_raw(
        self,
        raw: Dict[str, Any],
        order_type: str,
        quantity: float,
        price: Optional[float],
    ) -> OrderRecord:
        """Build an OrderRecord from a ccxt order dict."""
        state = self._map_state(raw.get("status", "open"))
        return OrderRecord(
            order_id=str(raw.get("id", "")),
            symbol=raw.get("symbol", ""),
            side=raw.get("side", ""),
            order_type=order_type,
            quantity=quantity,
            price=price,
            state=state,
            filled_quantity=float(raw.get("filled", 0.0) or 0.0),
            avg_fill_price=float(raw.get("average", 0.0) or 0.0),
            raw=raw,
        )

    def _update_record_from_raw(self, order_id: str, raw: Dict[str, Any]) -> OrderRecord:
        """Update or create an OrderRecord from a fresh raw response."""
        state = self._map_state(raw.get("status", "open"))
        existing = self._orders.get(order_id)
        if existing:
            existing.state = state
            existing.filled_quantity = float(raw.get("filled", 0.0) or 0.0)
            existing.avg_fill_price = float(raw.get("average", 0.0) or 0.0)
            existing.raw = raw
            existing.updated_at = datetime.now(timezone.utc)
            return existing

        record = OrderRecord(
            order_id=order_id,
            symbol=raw.get("symbol", ""),
            side=raw.get("side", ""),
            order_type=raw.get("type", "unknown"),
            quantity=float(raw.get("amount", 0.0) or 0.0),
            price=raw.get("price"),
            state=state,
            filled_quantity=float(raw.get("filled", 0.0) or 0.0),
            avg_fill_price=float(raw.get("average", 0.0) or 0.0),
            raw=raw,
        )
        self._orders[order_id] = record
        return record

    @staticmethod
    def _map_state(ccxt_status: str) -> OrderState:
        mapping = {
            "open": OrderState.OPEN,
            "closed": OrderState.FILLED,
            "canceled": OrderState.CANCELLED,
            "cancelled": OrderState.CANCELLED,
            "rejected": OrderState.FAILED,
            "expired": OrderState.CANCELLED,
            "partially_filled": OrderState.PARTIALLY_FILLED,
        }
        return mapping.get(ccxt_status.lower(), OrderState.OPEN)

    def _retry(self, func, *args, **kwargs):
        """Call *func* with exponential back-off."""
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return func(*args, **kwargs)
            except (ccxt.NetworkError, ccxt.RequestTimeout) as exc:
                last_exc = exc
                wait = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error attempt %d/%d for %s: %s. Retrying in %.1fs.",
                    attempt, self.retry_attempts, getattr(func, "__name__", str(func)), exc, wait,
                )
                time.sleep(wait)
            except ccxt.ExchangeError as exc:
                raise ExecutionError(f"Exchange error: {exc}") from exc
            except Exception as exc:
                raise ExecutionError(f"Unexpected error: {exc}") from exc
        raise ExecutionError(
            f"All {self.retry_attempts} retry attempts exhausted. Last: {last_exc}"
        )
