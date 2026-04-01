import uuid
from sqlalchemy import Column, String, ForeignKey, Numeric, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import func
from app.models.base import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exchange = Column(String(50), nullable=False)
    total_value_usdt = Column(Numeric(20, 8), default=0)
    available_usdt = Column(Numeric(20, 8), default=0)
    positions = Column(JSON, nullable=True, default=dict)
    daily_pnl = Column(Numeric(20, 8), default=0)
    total_pnl = Column(Numeric(20, 8), default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="portfolios")
