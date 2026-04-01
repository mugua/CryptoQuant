"""
Celery alert tasks.

* check_price_alerts  – evaluate active price alerts against current prices.
* send_notifications  – flush the notification queue to configured channels.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import redis

from app.config import get_settings
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(
    name="tasks.alert_tasks.check_price_alerts",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def check_price_alerts(self) -> Dict[str, Any]:
    """
    Evaluate all active price alerts against the latest cached prices.

    For each triggered alert the task:
    1. Marks the alert as triggered in Redis.
    2. Enqueues a notification for ``send_notifications`` to deliver.

    Returns
    -------
    dict
        Summary: triggered count, checked count, errors.
    """
    r = _get_redis()

    # Load active alerts.
    raw_alerts = r.get("active_price_alerts")
    if not raw_alerts:
        return {"checked": 0, "triggered": 0, "errors": []}

    try:
        alerts: List[Dict[str, Any]] = json.loads(raw_alerts)
    except Exception:
        return {"checked": 0, "triggered": 0, "errors": ["Failed to parse alerts"]}

    checked = 0
    triggered = 0
    errors: List[str] = []
    remaining_alerts: List[Dict[str, Any]] = []

    for alert in alerts:
        alert_id = alert.get("id", "unknown")
        user_id = alert.get("user_id")
        symbol = alert.get("symbol", "BTC/USDT")
        condition = alert.get("condition", "above")  # "above" | "below" | "change_pct"
        target_price = float(alert.get("target_price", 0))
        exchange_id = alert.get("exchange", "binance")

        try:
            # Get current price from cache.
            price_key = f"latest_price:{exchange_id}:{symbol}"
            price_raw = r.get(price_key)

            if price_raw is None:
                # Try fetching live.
                try:
                    from engine.data_feed import DataFeed
                    feed = DataFeed(exchange_id=exchange_id)
                    feed.connect()
                    ticker = feed.fetch_ticker(symbol)
                    feed.disconnect()
                    current_price = float(ticker.get("last", 0.0))
                    r.set(price_key, str(current_price), ex=60)
                except Exception as feed_exc:
                    logger.warning("Cannot fetch price for %s: %s", symbol, feed_exc)
                    remaining_alerts.append(alert)
                    continue
            else:
                current_price = float(price_raw)

            checked += 1

            # Evaluate condition.
            alert_fired = False
            if condition == "above" and current_price >= target_price:
                alert_fired = True
            elif condition == "below" and current_price <= target_price:
                alert_fired = True
            elif condition == "change_pct":
                reference = float(alert.get("reference_price", current_price))
                if reference > 0:
                    change_pct = (current_price - reference) / reference * 100
                    threshold = float(alert.get("change_threshold_pct", 5.0))
                    if abs(change_pct) >= threshold:
                        alert_fired = True

            if alert_fired:
                triggered += 1
                notification = {
                    "user_id": user_id,
                    "alert_id": alert_id,
                    "symbol": symbol,
                    "condition": condition,
                    "target_price": target_price,
                    "current_price": current_price,
                    "message": _build_alert_message(symbol, condition, target_price, current_price),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "channel": alert.get("channel", "in_app"),
                }
                # Enqueue notification.
                notif_key = "notification_queue"
                existing = r.get(notif_key)
                queue: List[Dict] = json.loads(existing) if existing else []
                queue.append(notification)
                r.set(notif_key, json.dumps(queue), ex=3600)
                logger.info("Alert triggered: user=%s symbol=%s condition=%s price=%.2f", user_id, symbol, condition, current_price)

                # Keep recurring alerts; remove one-shot alerts.
                if alert.get("recurring", False):
                    remaining_alerts.append(alert)
            else:
                remaining_alerts.append(alert)

        except Exception as exc:
            logger.exception("Error checking alert %s", alert_id)
            errors.append(f"alert {alert_id}: {exc}")
            remaining_alerts.append(alert)

    # Persist remaining active alerts.
    r.set("active_price_alerts", json.dumps(remaining_alerts), ex=86400)

    return {"checked": checked, "triggered": triggered, "errors": errors}


@celery_app.task(
    name="tasks.alert_tasks.send_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def send_notifications(self) -> Dict[str, Any]:
    """
    Drain the notification queue and deliver each pending notification via
    its configured channel (in_app, email, webhook).

    Returns
    -------
    dict
        Summary: sent count, failed count.
    """
    r = _get_redis()
    notif_key = "notification_queue"
    raw = r.get(notif_key)

    if not raw:
        return {"sent": 0, "failed": 0}

    try:
        queue: List[Dict[str, Any]] = json.loads(raw)
    except Exception:
        return {"sent": 0, "failed": 0}

    # Clear the queue immediately (optimistic) to avoid re-processing.
    r.delete(notif_key)

    sent = 0
    failed = 0
    undelivered: List[Dict[str, Any]] = []

    for notification in queue:
        channel = notification.get("channel", "in_app")
        try:
            if channel == "in_app":
                _deliver_in_app(notification, r)
                sent += 1
            elif channel == "email":
                _deliver_email(notification)
                sent += 1
            elif channel == "webhook":
                _deliver_webhook(notification)
                sent += 1
            else:
                # Unknown channel – store as in_app.
                _deliver_in_app(notification, r)
                sent += 1
        except Exception as exc:
            logger.error("Failed to deliver notification: %s – %s", notification.get("alert_id"), exc)
            failed += 1
            undelivered.append(notification)

    # Re-queue any failed notifications.
    if undelivered:
        r.set(notif_key, json.dumps(undelivered), ex=3600)

    return {"sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# Delivery helpers
# ---------------------------------------------------------------------------


def _build_alert_message(
    symbol: str,
    condition: str,
    target_price: float,
    current_price: float,
) -> str:
    """Build a human-readable alert message."""
    if condition == "above":
        return f"🔔 {symbol} price alert: current price {current_price:.4f} has risen above your target of {target_price:.4f}."
    if condition == "below":
        return f"🔔 {symbol} price alert: current price {current_price:.4f} has fallen below your target of {target_price:.4f}."
    return f"🔔 {symbol} price alert triggered at {current_price:.4f} (target: {target_price:.4f})."


def _deliver_in_app(notification: Dict[str, Any], r: redis.Redis) -> None:
    """Store the notification in the user's in-app notification list."""
    user_id = notification.get("user_id", "unknown")
    key = f"notifications:in_app:{user_id}"
    existing = r.get(key)
    items: List[Dict] = json.loads(existing) if existing else []
    items.append(notification)
    r.set(key, json.dumps(items[-100:]), ex=604800)  # keep 100 items, 7 days TTL


def _deliver_email(notification: Dict[str, Any]) -> None:
    """
    Send an email notification.

    In production this would integrate with SendGrid / SES etc.
    Currently logs the intent; replace with real SMTP/API call.
    """
    logger.info(
        "EMAIL notification to user %s: %s",
        notification.get("user_id"),
        notification.get("message"),
    )


def _deliver_webhook(notification: Dict[str, Any]) -> None:
    """
    POST the notification payload to a user-configured webhook URL.

    In production this would use httpx or requests.
    Currently logs the intent; replace with real HTTP call.
    """
    logger.info(
        "WEBHOOK notification to user %s: %s",
        notification.get("user_id"),
        notification.get("message"),
    )
