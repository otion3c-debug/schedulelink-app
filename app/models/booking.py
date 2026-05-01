from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from ..database import Base
from ._base import GUID, gen_uuid


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attendee_name = Column(String(255), nullable=False)
    attendee_email = Column(String(255), nullable=False, index=True)
    attendee_phone = Column(String(50))
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    timezone = Column(String(50), nullable=False)
    status = Column(String(20), default="confirmed")
    notes = Column(Text)
    calendar_event_id = Column(String(255))
    calendar_provider = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime)

    user = relationship("User", back_populates="bookings")

    __table_args__ = (
        CheckConstraint("status IN ('confirmed', 'cancelled', 'completed')", name="valid_booking_status"),
        CheckConstraint("start_time < end_time", name="valid_booking_time_range"),
    )
