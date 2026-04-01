import logging
import os
import uuid
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.user_api_key import UserApiKey
from app.models.user_session import UserSession
from app.models.notification import Notification
from app.models.operation_log import OperationLog
from app.schemas.user import (
    UserOut, UserUpdate, UserSettings, PasswordChange,
    TwoFASetup, TwoFAVerify, ApiKeyCreate, ApiKeyOut, SessionOut,
    NotificationSettings,
)
from app.schemas.notification import NotificationOut, NotificationPreferences
from app.schemas.operation_log import OperationLogOut, OperationLogFilter
from app.core.exceptions import NotFoundException, ValidationException
from app.services import user_service, notification_service, operation_log_service
from app.utils.helpers import make_paginated_response

logger = logging.getLogger(__name__)
router = APIRouter()

AVATAR_DIR = "static/avatars"


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await user_service.update_user_profile(db, current_user, user_update)
    await operation_log_service.log_operation(
        db, current_user.id, "update_profile", "user", str(current_user.id)
    )
    return updated


@router.put("/me/password", status_code=204)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await user_service.change_password(
        db, current_user, password_data.old_password, password_data.new_password
    )
    await operation_log_service.log_operation(
        db, current_user.id, "change_password", "user", str(current_user.id)
    )


@router.put("/me/settings", response_model=UserOut)
async def update_settings(
    settings_data: UserSettings,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await user_service.update_user_settings(db, current_user, settings_data)
    return updated


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise ValidationException("Only image files are allowed (JPEG, PNG, GIF, WebP)")
    os.makedirs(AVATAR_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"{current_user.id}.{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    current_user.avatar_url = f"/static/avatars/{filename}"
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("/me/2fa/setup", response_model=TwoFASetup)
async def setup_2fa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.two_fa_enabled:
        raise ValidationException("2FA is already enabled")
    return await user_service.setup_2fa(db, current_user)


@router.post("/me/2fa/verify", status_code=200)
async def verify_2fa(
    verify_data: TwoFAVerify,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    success = await user_service.verify_2fa(db, current_user, verify_data.totp_code)
    if not success:
        raise ValidationException("Invalid TOTP code")
    await operation_log_service.log_operation(
        db, current_user.id, "enable_2fa", "user", str(current_user.id)
    )
    return {"message": "2FA enabled successfully"}


@router.delete("/me/2fa", status_code=200)
async def disable_2fa(
    verify_data: TwoFAVerify,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    success = await user_service.disable_2fa(db, current_user, verify_data.totp_code)
    if not success:
        raise ValidationException("Invalid TOTP code")
    await operation_log_service.log_operation(
        db, current_user.id, "disable_2fa", "user", str(current_user.id)
    )
    return {"message": "2FA disabled successfully"}


@router.get("/me/2fa/recovery-codes")
async def get_recovery_codes(current_user: User = Depends(get_current_active_user)):
    if not current_user.two_fa_enabled:
        raise ValidationException("2FA is not enabled")
    import pyotp
    codes = [pyotp.random_base32()[:8] for _ in range(8)]
    return {"recovery_codes": codes}


@router.get("/me/sessions", response_model=List[SessionOut])
async def get_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        ).order_by(UserSession.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/me/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session not found")
    session.is_active = False
    await db.flush()


@router.get("/me/api-keys", response_model=List[ApiKeyOut])
async def get_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == current_user.id,
            UserApiKey.is_active == True,
        ).order_by(UserApiKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/me/api-keys", response_model=ApiKeyOut, status_code=201)
async def create_api_key(
    api_key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    api_key = await user_service.create_api_key(db, current_user, api_key_data)
    await operation_log_service.log_operation(
        db, current_user.id, "create_api_key", "api_key", str(api_key.id),
        details={"exchange": api_key_data.exchange}
    )
    return api_key


@router.put("/me/api-keys/{key_id}", response_model=ApiKeyOut)
async def update_api_key(
    key_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.id == key_id,
            UserApiKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise NotFoundException("API key not found")
    if "label" in update_data:
        api_key.label = update_data["label"]
    if "is_active" in update_data:
        api_key.is_active = update_data["is_active"]
    if "permissions" in update_data:
        api_key.permissions = update_data["permissions"]
    await db.flush()
    await db.refresh(api_key)
    return api_key


@router.delete("/me/api-keys/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await user_service.delete_api_key(db, key_id, current_user)
    await operation_log_service.log_operation(
        db, current_user.id, "delete_api_key", "api_key", key_id
    )


@router.post("/me/api-keys/{key_id}/test")
async def test_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await user_service.test_api_key(db, key_id, current_user)
    return result


@router.get("/me/notifications")
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    notifications = await notification_service.get_notifications(db, current_user.id, skip, limit)
    count_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
    )
    total = count_result.scalar_one() or 0
    items = [NotificationOut.model_validate(n) for n in notifications]
    return make_paginated_response(items, total, skip, limit)


@router.get("/me/notifications/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.put("/me/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await notification_service.mark_as_read(db, notification_id, current_user.id)
    return notification


@router.put("/me/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.mark_all_read(db, current_user.id)
    return {"marked_read": count}


@router.delete("/me/notifications/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.delete_notification(db, notification_id, current_user.id)


@router.get("/me/notification-settings", response_model=NotificationPreferences)
async def get_notification_settings(current_user: User = Depends(get_current_active_user)):
    # Return default settings - in a real system these would be stored per user
    return NotificationPreferences()


@router.put("/me/notification-settings", response_model=NotificationPreferences)
async def update_notification_settings(
    settings_data: NotificationPreferences,
    current_user: User = Depends(get_current_active_user),
):
    # In a real system, persist these to a user_notification_settings table
    return settings_data


@router.get("/me/operation-logs")
async def get_operation_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    log_filter = OperationLogFilter(action=action, resource_type=resource_type)
    logs = await operation_log_service.get_logs(db, current_user.id, log_filter, skip, limit)
    count_result = await db.execute(
        select(func.count(OperationLog.id)).where(OperationLog.user_id == current_user.id)
    )
    total = count_result.scalar_one() or 0
    items = [OperationLogOut.model_validate(log) for log in logs]
    return make_paginated_response(items, total, skip, limit)
