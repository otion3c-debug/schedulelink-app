from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from ._base import GUID, gen_uuid


class BookingType(Base):
    __tablename__ = "booking_types"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    description = Column(Text)
    color = Column(String(7), default="#3B82F6")
    is_active = Column(Boolean, default=True)
    buffer_before_minutes = Column(Integer, default=0)
    buffer_after_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="booking_types")
