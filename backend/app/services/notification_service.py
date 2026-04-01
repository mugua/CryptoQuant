import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.notification import Notification
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    content: str,
    notification_type: str,
    related_id: Optional[str] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        content=content,
        notification_type=notification_type,
        is_read=False,
        related_id=related_id,
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    logger.info(f"Notification created for user {user_id}: {title}")
    return notification


async def get_notifications(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 20
) -> List[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_unread_count(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    return result.scalar_one() or 0


async def mark_as_read(db: AsyncSession, notification_id: UUID, user_id: UUID) -> Notification:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundException("Notification not found")
    notification.is_read = True
    await db.flush()
    await db.refresh(notification)
    return notification


async def mark_all_read(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    notifications = list(result.scalars().all())
    count = len(notifications)
    for n in notifications:
        n.is_read = True
    await db.flush()
    return count


async def delete_notification(db: AsyncSession, notification_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundException("Notification not found")
    await db.delete(notification)
    await db.flush()
    return True
