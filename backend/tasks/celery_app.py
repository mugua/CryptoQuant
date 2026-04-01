"""
Celery application configuration.

Uses Redis as both the message broker and the result backend, matching the
settings defined in ``app.config``.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cryptoquant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.data_tasks",
        "tasks.trading_tasks",
        "tasks.alert_tasks",
    ],
)

celery_app.conf.update(
    # Serialisation.
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Broker connection retry on startup (Celery 5.3+, required in 6.0+).
    broker_connection_retry_on_startup=True,

    # Default queue – must match the queues the worker listens on.
    task_default_queue="default",

    # Result expiry (24 hours).
    result_expires=86400,

    # Beat schedule – periodic tasks.
    beat_schedule={
        "fetch-market-data-every-minute": {
            "task": "tasks.data_tasks.fetch_market_data",
            "schedule": 60.0,
            "args": (),
        },
        "update-portfolio-every-5-minutes": {
            "task": "tasks.data_tasks.update_portfolio",
            "schedule": 300.0,
        },
        "sync-orders-every-2-minutes": {
            "task": "tasks.data_tasks.sync_orders",
            "schedule": 120.0,
        },
        "execute-strategy-signals-every-minute": {
            "task": "tasks.trading_tasks.execute_strategy_signals",
            "schedule": 60.0,
        },
        "run-scheduled-backtest-every-hour": {
            "task": "tasks.trading_tasks.run_scheduled_backtest",
            "schedule": 3600.0,
        },
        "check-price-alerts-every-30-seconds": {
            "task": "tasks.alert_tasks.check_price_alerts",
            "schedule": 30.0,
        },
        "send-notifications-every-minute": {
            "task": "tasks.alert_tasks.send_notifications",
            "schedule": 60.0,
        },
    },

    # Worker settings.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
