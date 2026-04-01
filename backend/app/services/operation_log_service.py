import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.operation_log import OperationLog
from app.schemas.operation_log import OperationLogFilter

logger = logging.getLogger(__name__)


async def log_operation(
    db: AsyncSession,
    user_id: Optional[UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> OperationLog:
    log = OperationLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    logger.debug(f"Operation logged: {action} by user {user_id}")
    return log


async def get_logs(
    db: AsyncSession,
    user_id: UUID,
    log_filter: Optional[OperationLogFilter] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[OperationLog]:
    query = select(OperationLog).where(OperationLog.user_id == user_id)
    if log_filter:
        if log_filter.action:
            query = query.where(OperationLog.action.ilike(f"%{log_filter.action}%"))
        if log_filter.resource_type:
            query = query.where(OperationLog.resource_type == log_filter.resource_type)
        if log_filter.start_date:
            query = query.where(OperationLog.created_at >= log_filter.start_date)
        if log_filter.end_date:
            query = query.where(OperationLog.created_at <= log_filter.end_date)
    query = query.order_by(OperationLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
