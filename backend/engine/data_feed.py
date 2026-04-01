"""
Data feed module for fetching OHLCV data from cryptocurrency exchanges via ccxt.

Supports historical data fetching, multiple exchanges and symbols,
with retry logic and error handling.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import ccxt
import pandas as pd

logger = logging.getLogger(__name__)

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds


class DataFeedError(Exception):
    """Raised when data feed encounters an unrecoverable error."""


class DataFeed:
    """
    Connects to cryptocurrency exchanges via ccxt, fetches OHLCV data
    (historical and streaming), and normalises it into a pandas DataFrame.

    Parameters
    ----------
    exchange_id : str
        ccxt exchange identifier (e.g. ``"binance"``, ``"bybit"``).
    api_key : str, optional
        Exchange API key for authenticated endpoints.
    api_secret : str, optional
        Exchange API secret.
    sandbox : bool
        Use exchange sandbox / testnet when available.
    retry_attempts : int
        Number of retry attempts on transient errors.
    retry_delay : float
        Base delay in seconds between retries (exponential back-off applied).
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
        self._exchange: Optional[ccxt.Exchange] = None
        self._exchange_config: Dict[str, Any] = {
            "enableRateLimit": True,
        }
        if api_key:
            self._exchange_config["apiKey"] = api_key
        if api_secret:
            self._exchange_config["secret"] = api_secret
        self._sandbox = sandbox

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Instantiate the ccxt exchange object and load markets."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
        except AttributeError as exc:
            raise DataFeedError(f"Unknown exchange: {self.exchange_id}") from exc

        self._exchange = exchange_class(self._exchange_config)

        if self._sandbox and self._exchange.urls.get("test"):
            self._exchange.set_sandbox_mode(True)

        self._retry(self._exchange.load_markets)
        logger.info("Connected to exchange: %s", self.exchange_id)

    def disconnect(self) -> None:
        """Close the exchange connection (best-effort)."""
        if self._exchange is not None:
            try:
                if hasattr(self._exchange, "close"):
                    self._exchange.close()
            except Exception:
                pass
            self._exchange = None
        logger.info("Disconnected from exchange: %s", self.exchange_id)

    @property
    def exchange(self) -> ccxt.Exchange:
        if self._exchange is None:
            raise DataFeedError("Not connected. Call connect() first.")
        return self._exchange

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV candles for *symbol* on the connected exchange.

        Parameters
        ----------
        symbol : str
            Market symbol, e.g. ``"BTC/USDT"``.
        timeframe : str
            Candle timeframe supported by the exchange (e.g. ``"1m"``, ``"1h"``).
        since : datetime, optional
            Fetch candles starting from this UTC timestamp.
        limit : int
            Maximum number of candles to return per request.

        Returns
        -------
        pd.DataFrame
            Columns: open, high, low, close, volume; index: UTC DatetimeIndex.
        """
        since_ms: Optional[int] = None
        if since is not None:
            since_ms = int(since.timestamp() * 1000)

        raw = self._retry(
            self.exchange.fetch_ohlcv,
            symbol,
            timeframe,
            since_ms,
            limit,
        )
        return self._to_dataframe(raw)

    def fetch_ohlcv_history(
        self,
        symbol: str,
        timeframe: str = "1h",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        batch_size: int = 500,
    ) -> pd.DataFrame:
        """
        Fetch complete historical OHLCV data between *start* and *end* by
        paginating through the exchange API.

        Parameters
        ----------
        symbol : str
            Market symbol.
        timeframe : str
            Candle timeframe.
        start : datetime, optional
            Start of the history window (UTC). Defaults to exchange inception.
        end : datetime, optional
            End of the history window (UTC). Defaults to now.
        batch_size : int
            Number of candles per request.

        Returns
        -------
        pd.DataFrame
            Columns: open, high, low, close, volume; index: UTC DatetimeIndex.
        """
        if end is None:
            end = datetime.now(timezone.utc)

        since_ms: Optional[int] = None
        if start is not None:
            since_ms = int(start.timestamp() * 1000)

        end_ms = int(end.timestamp() * 1000)
        all_candles: List[List] = []

        while True:
            raw = self._retry(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                since_ms,
                batch_size,
            )
            if not raw:
                break

            # Filter out candles beyond the requested end date.
            filtered = [c for c in raw if c[0] <= end_ms]
            all_candles.extend(filtered)

            if len(filtered) < batch_size or raw[-1][0] >= end_ms:
                break

            # Advance cursor past the last candle received.
            since_ms = raw[-1][0] + 1

        if not all_candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = self._to_dataframe(all_candles)
        return df[df.index <= pd.Timestamp(end, tz="UTC")]

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Return the latest ticker for *symbol*."""
        return self._retry(self.exchange.fetch_ticker, symbol)

    def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Return the current order book for *symbol*."""
        return self._retry(self.exchange.fetch_order_book, symbol, limit)

    def get_supported_timeframes(self) -> List[str]:
        """Return timeframes supported by the connected exchange."""
        return list(self.exchange.timeframes.keys()) if self.exchange.timeframes else []

    def get_markets(self) -> Dict[str, Any]:
        """Return the exchange's market metadata."""
        return self.exchange.markets or {}

    # ------------------------------------------------------------------
    # Streaming (generator-based polling)
    # ------------------------------------------------------------------

    def stream_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        poll_interval: float = 5.0,
    ):
        """
        Yield the latest closed candle as a single-row DataFrame, polling
        the exchange every *poll_interval* seconds.

        This is a blocking generator; run it in a dedicated thread or process.

        Yields
        ------
        pd.DataFrame
            Single-row DataFrame with the latest closed candle.
        """
        last_ts: Optional[int] = None
        while True:
            try:
                raw = self._retry(self.exchange.fetch_ohlcv, symbol, timeframe, None, 2)
                if raw:
                    # Use the second-to-last candle (last *closed* candle).
                    candle = raw[-2] if len(raw) >= 2 else raw[-1]
                    if candle[0] != last_ts:
                        last_ts = candle[0]
                        yield self._to_dataframe([candle])
            except Exception as exc:  # noqa: BLE001
                logger.warning("Stream error for %s %s: %s", symbol, timeframe, exc)
            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dataframe(raw: List[List]) -> pd.DataFrame:
        """Convert raw ccxt OHLCV list to a normalised DataFrame."""
        df = pd.DataFrame(raw, columns=OHLCV_COLUMNS)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)
        df.sort_index(inplace=True)
        df = df[~df.index.duplicated(keep="last")]
        return df

    def _retry(self, func, *args, **kwargs):
        """
        Call *func* with exponential back-off retry logic.

        Raises
        ------
        DataFeedError
            When all retry attempts are exhausted.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return func(*args, **kwargs)
            except (ccxt.NetworkError, ccxt.RequestTimeout) as exc:
                last_exc = exc
                wait = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error on attempt %d/%d for %s: %s. Retrying in %.1fs.",
                    attempt,
                    self.retry_attempts,
                    getattr(func, "__name__", str(func)),
                    exc,
                    wait,
                )
                time.sleep(wait)
            except ccxt.ExchangeError as exc:
                raise DataFeedError(f"Exchange error: {exc}") from exc
            except Exception as exc:
                raise DataFeedError(f"Unexpected error: {exc}") from exc

        raise DataFeedError(
            f"All {self.retry_attempts} retry attempts exhausted. Last error: {last_exc}"
        )
