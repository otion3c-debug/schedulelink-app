from datetime import datetime
from sqlalchemy import Column, Integer, Time, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from ..database import Base
from ._base import GUID, gen_uuid


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="availability_rules")

    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="valid_day"),
        CheckConstraint("start_time < end_time", name="valid_time_range"),
    )
