"""
Celery data tasks.

* fetch_market_data – fetch and cache OHLCV data for active strategies.
* update_portfolio   – recompute portfolio mark-to-market values.
* sync_orders        – reconcile local order state with exchange state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import redis

from app.config import get_settings
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_active_strategy_configs() -> List[Dict[str, Any]]:
    """
    Return a list of active strategy configurations from Redis cache.

    In a full deployment this would query the database; here we read a
    Redis key ``active_strategies`` (a JSON list) populated by the API.
    """
    r = _get_redis()
    import json

    raw = r.get("active_strategies")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(
    name="tasks.data_tasks.fetch_market_data",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def fetch_market_data(self) -> Dict[str, Any]:
    """
    Periodic task: fetch OHLCV data for all active strategies and cache
    the latest candle in Redis.

    Returns
    -------
    dict
        Summary of symbols processed.
    """
    from engine.data_feed import DataFeed, DataFeedError
    import json

    r = _get_redis()
    configs = _get_active_strategy_configs()
    processed: List[str] = []
    errors: List[str] = []

    # Deduplicate (exchange, symbol, timeframe) tuples.
    seen = set()
    targets = []
    for cfg in configs:
        key = (cfg.get("exchange", "binance"), cfg.get("symbol", "BTC/USDT"), cfg.get("timeframe", "1h"))
        if key not in seen:
            seen.add(key)
            targets.append(key)

    for exchange_id, symbol, timeframe in targets:
        try:
            feed = DataFeed(exchange_id=exchange_id)
            feed.connect()
            df = feed.fetch_ohlcv(symbol, timeframe, limit=200)
            feed.disconnect()

            cache_key = f"ohlcv:{exchange_id}:{symbol}:{timeframe}"
            # Store as JSON-serialisable list of records.
            records = df.reset_index().rename(columns={"timestamp": "ts"})
            records["ts"] = records["ts"].astype(str)
            r.set(cache_key, json.dumps(records.to_dict("records")), ex=3600)
            processed.append(f"{exchange_id}:{symbol}:{timeframe}")
            logger.info("Fetched OHLCV %s:%s:%s  rows=%d", exchange_id, symbol, timeframe, len(df))

        except DataFeedError as exc:
            logger.error("DataFeed error for %s:%s:%s – %s", exchange_id, symbol, timeframe, exc)
            errors.append(f"{exchange_id}:{symbol}:{timeframe} – {exc}")
        except Exception as exc:
            logger.exception("Unexpected error fetching %s:%s:%s", exchange_id, symbol, timeframe)
            errors.append(str(exc))

    return {"processed": processed, "errors": errors}


@celery_app.task(
    name="tasks.data_tasks.update_portfolio",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def update_portfolio(self) -> Dict[str, Any]:
    """
    Periodic task: update portfolio mark-to-market values for all users
    with active API keys by fetching current prices from exchanges.

    Returns
    -------
    dict
        Counts of updated and failed portfolios.
    """
    import json
    from engine.data_feed import DataFeed, DataFeedError

    r = _get_redis()
    raw = r.get("active_portfolios")
    if not raw:
        return {"updated": 0, "errors": 0}

    try:
        portfolios = json.loads(raw)
    except Exception:
        return {"updated": 0, "errors": 0}

    updated = 0
    errors = 0

    for portfolio in portfolios:
        user_id = portfolio.get("user_id")
        exchange_id = portfolio.get("exchange", "binance")
        symbols: List[str] = portfolio.get("symbols", [])

        try:
            feed = DataFeed(exchange_id=exchange_id)
            feed.connect()
            prices = {}
            for symbol in symbols:
                ticker = feed.fetch_ticker(symbol)
                prices[symbol] = float(ticker.get("last", 0.0))
            feed.disconnect()

            cache_key = f"prices:{user_id}:{exchange_id}"
            r.set(cache_key, json.dumps(prices), ex=600)
            updated += 1
            logger.info("Updated portfolio prices for user %s on %s", user_id, exchange_id)

        except (DataFeedError, Exception) as exc:
            logger.error("Portfolio update failed for user %s: %s", user_id, exc)
            errors += 1

    return {"updated": updated, "errors": errors}


@celery_app.task(
    name="tasks.data_tasks.sync_orders",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def sync_orders(self) -> Dict[str, Any]:
    """
    Periodic task: synchronise open orders from exchanges and update the
    local order cache in Redis.

    Returns
    -------
    dict
        Counts of synced and failed order sets.
    """
    import json
    from engine.execution import ExecutionEngine, ExecutionError

    r = _get_redis()
    raw = r.get("active_api_keys")
    if not raw:
        return {"synced": 0, "errors": 0}

    try:
        api_keys = json.loads(raw)
    except Exception:
        return {"synced": 0, "errors": 0}

    synced = 0
    errors = 0

    for entry in api_keys:
        uid = str(entry.get("user_id", ""))
        exch = str(entry.get("exchange", "binance"))

        try:
            engine = ExecutionEngine(
                exchange_id=exch,
                api_key=entry.get("api_key", ""),
                api_secret=entry.get("api_secret", ""),
            )
            engine.connect()
            open_orders = engine.get_open_orders()
            engine.disconnect()

            orders_data = [
                {
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "side": o.side,
                    "state": o.state.value,
                    "quantity": o.quantity,
                    "filled": o.filled_quantity,
                    "price": o.price,
                }
                for o in open_orders
            ]
            cache_key = f"open_orders:{uid}:{exch}"
            r.set(cache_key, json.dumps(orders_data), ex=600)
            synced += 1
            logger.info("Synced %d open orders for user=%s exchange=%s", len(open_orders), uid, exch)

        except Exception as exc:
            logger.error("Order sync failed for user=%s exchange=%s: %s", uid, exch, exc)
            errors += 1

    return {"synced": synced, "errors": errors}
