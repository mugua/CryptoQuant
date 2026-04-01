import logging
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertUpdate
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


async def create_alert(db: AsyncSession, user_id: UUID, alert_create: AlertCreate) -> Alert:
    alert = Alert(
        user_id=user_id,
        name=alert_create.name,
        alert_type=alert_create.alert_type,
        exchange=alert_create.exchange,
        symbol=alert_create.symbol,
        condition=alert_create.condition,
        threshold=alert_create.threshold,
        is_active=alert_create.is_active,
        is_triggered=False,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    logger.info(f"Alert created: {alert.name} for user {user_id}")
    return alert


async def get_alerts(db: AsyncSession, user_id: UUID) -> List[Alert]:
    result = await db.execute(
        select(Alert).where(Alert.user_id == user_id).order_by(Alert.created_at.desc())
    )
    return list(result.scalars().all())


async def get_alert(db: AsyncSession, alert_id: UUID, user_id: UUID) -> Alert:
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise NotFoundException("Alert not found")
    return alert


async def update_alert(
    db: AsyncSession, alert_id: UUID, user_id: UUID, update: AlertUpdate
) -> Alert:
    alert = await get_alert(db, alert_id, user_id)
    if update.name is not None:
        alert.name = update.name
    if update.condition is not None:
        alert.condition = update.condition
    if update.threshold is not None:
        alert.threshold = update.threshold
    if update.is_active is not None:
        alert.is_active = update.is_active
    await db.flush()
    await db.refresh(alert)
    return alert


async def delete_alert(db: AsyncSession, alert_id: UUID, user_id: UUID) -> bool:
    alert = await get_alert(db, alert_id, user_id)
    await db.delete(alert)
    await db.flush()
    return True


def evaluate_alert(alert: Alert, current_price: Decimal) -> bool:
    """Evaluate whether an alert condition is met given current price."""
    threshold = Decimal(str(alert.threshold))
    condition = alert.condition
    if condition == "gt":
        return current_price > threshold
    elif condition == "lt":
        return current_price < threshold
    elif condition == "gte":
        return current_price >= threshold
    elif condition == "lte":
        return current_price <= threshold
    elif condition in ("crosses_above", "crosses_below"):
        # For crosses conditions, treat same as gt/lt for point-in-time checks
        if condition == "crosses_above":
            return current_price > threshold
        else:
            return current_price < threshold
    return False


async def trigger_alert(db: AsyncSession, alert: Alert, notification_service) -> None:
    """Mark alert as triggered and create a notification."""
    alert.is_triggered = True
    alert.last_triggered_at = datetime.now(timezone.utc)
    await db.flush()
    await notification_service.create_notification(
        db=db,
        user_id=alert.user_id,
        title=f"Alert Triggered: {alert.name}",
        content=(
            f"Your alert '{alert.name}' for {alert.symbol} on {alert.exchange} "
            f"has been triggered. Condition: {alert.condition} {alert.threshold}"
        ),
        notification_type="alert",
        related_id=str(alert.id),
    )
    logger.info(f"Alert triggered: {alert.name} for user {alert.user_id}")
