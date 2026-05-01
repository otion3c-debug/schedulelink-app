from datetime import datetime, date
from sqlalchemy import Column, String, Integer, DateTime, Date, CheckConstraint, Index
from sqlalchemy.orm import relationship
from ..database import Base
from ._base import GUID, gen_uuid


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    timezone = Column(String(50), default="America/New_York")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    subscription_tier = Column(String(20), default="free")
    subscription_status = Column(String(20), default="active")
    stripe_customer_id = Column(String(255), unique=True)
    stripe_subscription_id = Column(String(255))
    booking_slug = Column(String(100), unique=True, nullable=False, index=True)
    booking_limit = Column(Integer, default=5)
    bookings_used_this_month = Column(Integer, default=0)
    billing_cycle_start = Column(Date)

    calendar_connections = relationship("CalendarConnection", back_populates="user", cascade="all, delete-orphan")
    availability_rules = relationship("AvailabilityRule", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    booking_types = relationship("BookingType", back_populates="user", cascade="all, delete-orphan")
    widget_customization = relationship("WidgetCustomization", back_populates="user", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        CheckConstraint("subscription_tier IN ('free', 'pro', 'pro_plus')", name="valid_tier"),
        CheckConstraint("subscription_status IN ('active', 'cancelled', 'expired')", name="valid_status"),
    )
