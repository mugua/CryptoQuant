from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ThemeMode(str, Enum):
    light = "light"
    dark = "dark"
    auto = "auto"


class Language(str, Enum):
    zh_CN = "zh-CN"
    en_US = "en-US"


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    email: str
    username: str
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    theme_mode: ThemeMode
    language: Language
    timezone: str
    default_exchange: Optional[str] = None
    default_timeframe: Optional[str] = None
    two_fa_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    phone: Optional[str] = None
    timezone: Optional[str] = None
    default_exchange: Optional[str] = None
    default_timeframe: Optional[str] = None


class UserSettings(BaseModel):
    theme_mode: Optional[ThemeMode] = None
    language: Optional[Language] = None
    timezone: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class TwoFASetup(BaseModel):
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class TwoFAVerify(BaseModel):
    totp_code: str


class ApiKeyCreate(BaseModel):
    exchange: str
    api_key: str
    api_secret: str
    label: Optional[str] = None
    permissions: Optional[List[str]] = None


class ApiKeyOut(BaseModel):
    id: UUID
    exchange: str
    label: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: bool
    last_tested_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionOut(BaseModel):
    id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    last_active_at: Optional[datetime] = None
    expires_at: datetime
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSettings(BaseModel):
    email_alerts: bool = True
    push_alerts: bool = True
    trade_notifications: bool = True
    system_notifications: bool = True
