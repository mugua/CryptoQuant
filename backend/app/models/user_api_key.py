from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class UserApiKey(BaseModel):
    __tablename__ = "user_api_keys"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exchange = Column(String(50), nullable=False)
    api_key_encrypted = Column(String(500), nullable=False)
    api_secret_encrypted = Column(String(500), nullable=False)
    label = Column(String(100), nullable=True)
    permissions = Column(JSON, nullable=True, default=list)
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="api_keys")
