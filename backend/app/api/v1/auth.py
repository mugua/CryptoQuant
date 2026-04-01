import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import pyotp

from app.db.session import get_db
from app.schemas.user import UserCreate, UserLogin, Token, TokenRefresh
from app.models.user import User
from app.models.user_session import UserSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_token,
    get_password_hash,
)
from app.core.exceptions import AuthException, ValidationException
from app.services import user_service
from app.api.deps import get_current_active_user
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=Token, status_code=201)
async def register(
    user_create: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and return tokens."""
    user = await user_service.register_user(db, user_create)
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    token_hash = hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at,
        is_active=True,
    )
    db.add(session)
    await db.commit()
    logger.info(f"User registered and logged in: {user.email}")
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens."""
    user = await user_service.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise AuthException("Invalid email or password")
    if not user.is_active:
        raise AuthException("Account is deactivated")
    # Check 2FA
    if user.two_fa_enabled:
        if not credentials.totp_code:
            raise AuthException("2FA code required")
        totp = pyotp.TOTP(user.two_fa_secret)
        if not totp.verify(credentials.totp_code, valid_window=1):
            raise AuthException("Invalid 2FA code")
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    token_hash = hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        last_active_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        is_active=True,
    )
    db.add(session)
    await db.commit()
    logger.info(f"User logged in: {user.email}")
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    payload = verify_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthException("Invalid or expired refresh token")
    user_id = payload.get("sub")
    if not user_id:
        raise AuthException("Invalid token payload")
    token_hash = hash_token(token_data.refresh_token)
    result = await db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.is_active == True,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise AuthException("Session not found or expired")
    if session.expires_at < datetime.now(timezone.utc):
        session.is_active = False
        await db.commit()
        raise AuthException("Session expired")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthException("User not found or inactive")
    # Rotate refresh token
    session.is_active = False
    new_access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    new_token_hash = hash_token(new_refresh_token)
    new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_session = UserSession(
        user_id=user.id,
        token_hash=new_token_hash,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        last_active_at=datetime.now(timezone.utc),
        expires_at=new_expires_at,
        is_active=True,
    )
    db.add(new_session)
    await db.commit()
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=204)
async def logout(
    token_data: TokenRefresh,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout current session."""
    token_hash = hash_token(token_data.refresh_token)
    result = await db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session:
        session.is_active = False
        await db.commit()
    logger.info(f"User logged out: {current_user.email}")


@router.post("/logout-all", status_code=204)
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Invalidate all active sessions for the current user."""
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        )
    )
    sessions = result.scalars().all()
    for session in sessions:
        session.is_active = False
    await db.commit()
    logger.info(f"All sessions invalidated for user: {current_user.email}")
