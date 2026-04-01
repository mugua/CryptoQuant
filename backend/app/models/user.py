import enum
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ThemeMode(str, enum.Enum):
    light = "light"
    dark = "dark"
    auto = "auto"


class Language(str, enum.Enum):
    zh_CN = "zh-CN"
    en_US = "en-US"


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    theme_mode = Column(SAEnum(ThemeMode), default=ThemeMode.auto)
    language = Column(SAEnum(Language), default=Language.zh_CN)
    timezone = Column(String(50), default="UTC")
    default_exchange = Column(String(50), nullable=True)
    default_timeframe = Column(String(10), nullable=True)
    two_fa_secret = Column(String(64), nullable=True)
    two_fa_enabled = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    strategies = relationship("Strategy", back_populates="user", lazy="dynamic")
    orders = relationship("Order", back_populates="user", lazy="dynamic")
    trades = relationship("Trade", back_populates="user", lazy="dynamic")
    alerts = relationship("Alert", back_populates="user", lazy="dynamic")
    notifications = relationship("Notification", back_populates="user", lazy="dynamic")
    api_keys = relationship("UserApiKey", back_populates="user", lazy="dynamic")
    sessions = relationship("UserSession", back_populates="user", lazy="dynamic")
    operation_logs = relationship("OperationLog", back_populates="user", lazy="dynamic")
    portfolios = relationship("Portfolio", back_populates="user", lazy="dynamic")
