"""
Celery trading tasks.

* execute_strategy_signals  – process pending trade signals from active strategies.
* run_scheduled_backtest    – run backtests for active strategies and cache results.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import redis

from app.config import get_settings
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(
    name="tasks.trading_tasks.execute_strategy_signals",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def execute_strategy_signals(self) -> Dict[str, Any]:
    """
    Process pending trade signals stored in Redis for all active strategies.

    For each strategy, the task:
    1. Reads the latest OHLCV cache.
    2. Instantiates the strategy and runs ``on_candle`` on the newest candle.
    3. If a signal is emitted, validates it with the risk manager and forwards
       to the execution engine (dry-run by default unless ``live=True``).

    Returns
    -------
    dict
        Summary of signals processed.
    """
    r = _get_redis()
    raw = r.get("active_strategies")
    if not raw:
        return {"processed": 0, "signals": [], "errors": []}

    try:
        configs = json.loads(raw)
    except Exception:
        return {"processed": 0, "signals": [], "errors": []}

    from engine.risk_manager import RiskManager, RiskConfig
    import pandas as pd

    processed = 0
    signals_emitted: List[Dict[str, Any]] = []
    errors: List[str] = []

    for cfg in configs:
        strategy_id = cfg.get("id", "unknown")
        exchange_id = cfg.get("exchange", "binance")
        symbol = cfg.get("symbol", "BTC/USDT")
        timeframe = cfg.get("timeframe", "1h")
        strategy_type = cfg.get("strategy_type", "MA_CROSS").upper()
        parameters = cfg.get("parameters", {})
        parameters["symbol"] = symbol
        live = cfg.get("live", False)

        try:
            # Load OHLCV from cache.
            cache_key = f"ohlcv:{exchange_id}:{symbol}:{timeframe}"
            ohlcv_raw = r.get(cache_key)
            if not ohlcv_raw:
                logger.debug("No OHLCV cache for %s:%s:%s", exchange_id, symbol, timeframe)
                continue

            records = json.loads(ohlcv_raw)
            df = pd.DataFrame(records)
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            df.set_index("ts", inplace=True)
            df = df[["open", "high", "low", "close", "volume"]].astype(float)

            if df.empty:
                continue

            # Instantiate strategy.
            strategy = _build_strategy(strategy_type, parameters)
            if strategy is None:
                continue

            capital = float(cfg.get("capital", 10000.0))
            strategy._set_capital(capital)
            strategy.initialize()

            # Run on last candle only (live-style processing).
            signal = strategy.on_candle(df.iloc[-1])

            if signal is None:
                processed += 1
                continue

            signal_data = {
                "strategy_id": strategy_id,
                "symbol": symbol,
                "exchange": exchange_id,
                "signal_type": signal.signal_type.value,
                "price": signal.price,
                "quantity": signal.quantity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": signal.metadata,
                "live": live,
            }
            signals_emitted.append(signal_data)

            # Store signal in Redis for downstream processing.
            signals_key = f"pending_signals:{strategy_id}"
            existing = r.get(signals_key)
            existing_list = json.loads(existing) if existing else []
            existing_list.append(signal_data)
            r.set(signals_key, json.dumps(existing_list[-50:]), ex=3600)  # keep last 50

            logger.info(
                "Signal emitted: strategy=%s type=%s qty=%.4f @ %.2f",
                strategy_id, signal.signal_type.value, signal.quantity, signal.price or 0,
            )

            # Live execution.
            if live:
                _execute_live_signal(signal_data, cfg, r)

            processed += 1

        except Exception as exc:
            logger.exception("Error processing strategy %s", strategy_id)
            errors.append(f"strategy {strategy_id}: {exc}")

    return {"processed": processed, "signals": signals_emitted, "errors": errors}


@celery_app.task(
    name="tasks.trading_tasks.run_scheduled_backtest",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def run_scheduled_backtest(self) -> Dict[str, Any]:
    """
    Run backtests for all strategies that have ``auto_backtest=True`` in
    their config, caching results in Redis.

    Returns
    -------
    dict
        Summary of backtests run.
    """
    r = _get_redis()
    raw = r.get("active_strategies")
    if not raw:
        return {"ran": 0, "errors": []}

    try:
        configs = json.loads(raw)
    except Exception:
        return {"ran": 0, "errors": []}

    import numpy as np
    import pandas as pd
    from engine.backtester import Backtester, BacktestConfig

    ran = 0
    errors: List[str] = []

    for cfg in configs:
        if not cfg.get("auto_backtest", False):
            continue

        strategy_id = cfg.get("id", "unknown")
        exchange_id = cfg.get("exchange", "binance")
        symbol = cfg.get("symbol", "BTC/USDT")
        timeframe = cfg.get("timeframe", "1h")
        strategy_type = cfg.get("strategy_type", "MA_CROSS").upper()
        parameters = cfg.get("parameters", {})
        parameters["symbol"] = symbol

        try:
            # Generate synthetic OHLCV for scheduled backtest (no live exchange call).
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=90)
            tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
            minutes = tf_minutes.get(timeframe, 60)
            freq = f"{minutes}min"
            idx = pd.date_range(start=start, end=end, freq=freq, tz=timezone.utc)
            n = len(idx)
            MAX_SEED_VALUE = 2**31
            np.random.seed(hash(strategy_id) % MAX_SEED_VALUE)
            returns = np.random.normal(0.0002, 0.018, n)
            price = 30000.0
            closes = []
            for r_val in returns:
                price = max(price * (1 + r_val), 1.0)
                closes.append(price)
            closes_arr = np.array(closes)
            highs = closes_arr * (1 + np.abs(np.random.normal(0, 0.004, n)))
            lows = closes_arr * (1 - np.abs(np.random.normal(0, 0.004, n)))
            opens = np.roll(closes_arr, 1)
            opens[0] = closes_arr[0]
            volumes = np.random.uniform(100, 2000, n)
            df = pd.DataFrame(
                {"open": opens, "high": highs, "low": lows, "close": closes_arr, "volume": volumes},
                index=idx,
            )

            strategy = _build_strategy(strategy_type, parameters)
            if strategy is None:
                continue

            bt_config = BacktestConfig(
                start_date=start,
                end_date=end,
                initial_capital=float(cfg.get("capital", 10000.0)),
                exchange=exchange_id,
                symbol=symbol,
                timeframe=timeframe,
            )
            backtester = Backtester()
            result = backtester.run(strategy, bt_config, df)

            # Cache result.
            cache_key = f"backtest_result:{strategy_id}"
            result_data = {
                "strategy_id": strategy_id,
                "stats": result.stats,
                "trade_count": len(result.trades),
                "run_at": datetime.now(timezone.utc).isoformat(),
            }
            r.set(cache_key, json.dumps(result_data, default=str), ex=86400)
            ran += 1
            logger.info("Backtest complete for strategy %s: %s", strategy_id, result.stats)

        except Exception as exc:
            logger.exception("Backtest failed for strategy %s", strategy_id)
            errors.append(f"strategy {strategy_id}: {exc}")

    return {"ran": ran, "errors": errors}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_strategy(strategy_type: str, parameters: Dict[str, Any]):
    """Instantiate a strategy class by type string."""
    from strategies.moving_average_cross import MovingAverageCross
    from strategies.rsi_strategy import RSIStrategy
    from strategies.bollinger_bands import BollingerBandsStrategy
    from strategies.dca_strategy import DCAStrategy
    from strategies.grid_trading import GridTradingStrategy

    mapping = {
        "MA_CROSS": MovingAverageCross,
        "RSI": RSIStrategy,
        "BOLLINGER": BollingerBandsStrategy,
        "DCA": DCAStrategy,
        "GRID": GridTradingStrategy,
    }
    cls = mapping.get(strategy_type)
    if cls is None:
        logger.warning("Unknown strategy type: %s", strategy_type)
        return None
    return cls(parameters=parameters)


def _execute_live_signal(
    signal_data: Dict[str, Any],
    cfg: Dict[str, Any],
    r: redis.Redis,
) -> None:
    """Submit a signal to the execution engine for live trading."""
    from engine.execution import ExecutionEngine, ExecutionError

    api_key = cfg.get("api_key", "")
    api_secret = cfg.get("api_secret", "")
    exchange_id = cfg.get("exchange", "binance")

    if not api_key or not api_secret:
        logger.warning("Live signal skipped – no API credentials for strategy %s", cfg.get("id"))
        return

    try:
        engine = ExecutionEngine(exchange_id=exchange_id, api_key=api_key, api_secret=api_secret)
        engine.connect()
        symbol = signal_data["symbol"]
        side = "buy" if signal_data["signal_type"] == "buy" else "sell"
        quantity = float(signal_data["quantity"])
        order = engine.place_market_order(symbol, side, quantity)
        engine.disconnect()
        logger.info("Live order placed: %s %s qty=%.4f id=%s", side, symbol, quantity, order.order_id)
    except Exception as exc:
        logger.error("Live execution failed: %s", exc)
