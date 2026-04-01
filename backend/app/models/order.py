from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Order(BaseModel):
    __tablename__ = "orders"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    price = Column(Numeric(20, 8), nullable=True)
    quantity = Column(Numeric(20, 8), nullable=False)
    filled_quantity = Column(Numeric(20, 8), default=0)
    status = Column(String(20), default="pending")
    exchange_order_id = Column(String(100), nullable=True)

    user = relationship("User", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    trades = relationship("Trade", back_populates="order", lazy="dynamic")
