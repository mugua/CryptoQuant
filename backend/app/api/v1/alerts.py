import logging
from typing import List
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertUpdate, AlertOut
from app.services import alert_service, notification_service
from app.utils.helpers import make_paginated_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=dict)
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    alerts = await alert_service.get_alerts(db, current_user.id)
    total = len(alerts)
    items = [AlertOut.model_validate(a) for a in alerts[skip:skip + limit]]
    return make_paginated_response(items, total, skip, limit)


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    alert_create: AlertCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await alert_service.create_alert(db, current_user.id, alert_create)


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await alert_service.get_alert(db, alert_id, current_user.id)


@router.put("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: UUID,
    alert_update: AlertUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await alert_service.update_alert(db, alert_id, current_user.id, alert_update)


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await alert_service.delete_alert(db, alert_id, current_user.id)


@router.post("/{alert_id}/test")
async def test_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually test an alert by evaluating it with a mock current price equal to threshold."""
    alert = await alert_service.get_alert(db, alert_id, current_user.id)
    # Simulate trigger: use threshold as mock price (condition gt/gte will not trigger, use lt)
    mock_price = Decimal(str(alert.threshold))
    triggered = alert_service.evaluate_alert(alert, mock_price * Decimal("0.99"))
    if triggered:
        await alert_service.trigger_alert(db, alert, notification_service)
    return {
        "alert_id": str(alert_id),
        "triggered": triggered,
        "mock_price": float(mock_price * Decimal("0.99")),
        "threshold": float(alert.threshold),
    }
