import logging
from typing import Optional
from datetime import datetime, timezone
import pyotp
import qrcode
import io
import base64
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.models.user_api_key import UserApiKey
from app.schemas.user import UserCreate, UserUpdate, UserSettings, TwoFASetup, ApiKeyCreate
from app.core.security import get_password_hash, verify_password, encrypt_api_key, decrypt_api_key
from app.core.exceptions import NotFoundException, ValidationException, AuthException

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, user_create: UserCreate) -> User:
    result = await db.execute(select(User).where(User.email == user_create.email))
    if result.scalar_one_or_none():
        raise ValidationException("Email already registered")
    result = await db.execute(select(User).where(User.username == user_create.username))
    if result.scalar_one_or_none():
        raise ValidationException("Username already taken")
    user = User(
        email=user_create.email,
        username=user_create.username,
        hashed_password=get_password_hash(user_create.password),
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info(f"Registered new user: {user.email}")
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise AuthException("Account is temporarily locked due to too many failed login attempts")
    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            from datetime import timedelta
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            logger.warning(f"Account locked due to too many failed attempts: {email}")
        await db.flush()
        return None
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.flush()
    return user


async def update_user_profile(db: AsyncSession, user: User, user_update: UserUpdate) -> User:
    if user_update.username is not None:
        result = await db.execute(
            select(User).where(User.username == user_update.username, User.id != user.id)
        )
        if result.scalar_one_or_none():
            raise ValidationException("Username already taken")
        user.username = user_update.username
    if user_update.phone is not None:
        user.phone = user_update.phone
    if user_update.timezone is not None:
        user.timezone = user_update.timezone
    if user_update.default_exchange is not None:
        user.default_exchange = user_update.default_exchange
    if user_update.default_timeframe is not None:
        user.default_timeframe = user_update.default_timeframe
    await db.flush()
    await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> bool:
    if not verify_password(old_password, user.hashed_password):
        raise ValidationException("Current password is incorrect")
    user.hashed_password = get_password_hash(new_password)
    await db.flush()
    return True


async def update_user_settings(db: AsyncSession, user: User, settings_update: UserSettings) -> User:
    if settings_update.theme_mode is not None:
        user.theme_mode = settings_update.theme_mode
    if settings_update.language is not None:
        user.language = settings_update.language
    if settings_update.timezone is not None:
        user.timezone = settings_update.timezone
    await db.flush()
    await db.refresh(user)
    return user


async def setup_2fa(db: AsyncSession, user: User) -> TwoFASetup:
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="CryptoQuant")
    qr = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    qr_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    qr_code_url = f"data:image/png;base64,{qr_base64}"
    # Store secret temporarily (not enabled until verified)
    user.two_fa_secret = secret
    await db.flush()
    # Generate backup codes
    backup_codes = [pyotp.random_base32()[:8] for _ in range(8)]
    logger.info(f"2FA setup initiated for user: {user.email}")
    return TwoFASetup(secret=secret, qr_code_url=qr_code_url, backup_codes=backup_codes)


async def verify_2fa(db: AsyncSession, user: User, totp_code: str) -> bool:
    if not user.two_fa_secret:
        raise ValidationException("2FA setup not initiated")
    totp = pyotp.TOTP(user.two_fa_secret)
    if not totp.verify(totp_code, valid_window=1):
        return False
    user.two_fa_enabled = True
    await db.flush()
    logger.info(f"2FA enabled for user: {user.email}")
    return True


async def disable_2fa(db: AsyncSession, user: User, totp_code: str) -> bool:
    if not user.two_fa_enabled or not user.two_fa_secret:
        raise ValidationException("2FA is not enabled")
    totp = pyotp.TOTP(user.two_fa_secret)
    if not totp.verify(totp_code, valid_window=1):
        return False
    user.two_fa_enabled = False
    user.two_fa_secret = None
    await db.flush()
    logger.info(f"2FA disabled for user: {user.email}")
    return True


async def create_api_key(db: AsyncSession, user: User, api_key_create: ApiKeyCreate) -> UserApiKey:
    encrypted_key = encrypt_api_key(api_key_create.api_key)
    encrypted_secret = encrypt_api_key(api_key_create.api_secret)
    api_key = UserApiKey(
        user_id=user.id,
        exchange=api_key_create.exchange,
        api_key_encrypted=encrypted_key,
        api_secret_encrypted=encrypted_secret,
        label=api_key_create.label,
        permissions=api_key_create.permissions or ["read"],
        is_active=True,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    logger.info(f"API key created for user {user.email} on exchange {api_key.exchange}")
    return api_key


async def test_api_key(db: AsyncSession, key_id: str, user: User) -> dict:
    import ccxt.async_support as ccxt_async
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.id == key_id, UserApiKey.user_id == user.id)
    )
    api_key_record = result.scalar_one_or_none()
    if not api_key_record:
        raise NotFoundException("API key not found")
    try:
        plain_key = decrypt_api_key(api_key_record.api_key_encrypted)
        plain_secret = decrypt_api_key(api_key_record.api_secret_encrypted)
        exchange_class = getattr(ccxt_async, api_key_record.exchange, None)
        if exchange_class is None:
            raise ValidationException(f"Unsupported exchange: {api_key_record.exchange}")
        exchange = exchange_class({"apiKey": plain_key, "secret": plain_secret})
        try:
            balance = await exchange.fetch_balance()
            total = balance.get("total", {})
            api_key_record.last_tested_at = datetime.now(timezone.utc)
            await db.flush()
            return {"success": True, "balance": {k: v for k, v in total.items() if v and v > 0}}
        finally:
            await exchange.close()
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"API key test failed for exchange {api_key_record.exchange}: {type(e).__name__}")
        return {"success": False, "error": "Exchange connection failed. Please verify your API credentials."}


async def delete_api_key(db: AsyncSession, key_id: str, user: User) -> bool:
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.id == key_id, UserApiKey.user_id == user.id)
    )
    api_key_record = result.scalar_one_or_none()
    if not api_key_record:
        raise NotFoundException("API key not found")
    await db.delete(api_key_record)
    await db.flush()
    return True
