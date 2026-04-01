from sqlalchemy import Column, String, Boolean, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Strategy(BaseModel):
    __tablename__ = "strategies"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=True, default=dict)
    is_active = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)

    user = relationship("User", back_populates="strategies")
    orders = relationship("Order", back_populates="strategy", lazy="dynamic")
    trades = relationship("Trade", back_populates="strategy", lazy="dynamic")
