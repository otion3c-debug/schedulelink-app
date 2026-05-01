from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship
from ..database import Base
from ._base import GUID, gen_uuid


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(20), nullable=False)
    provider_account_email = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    calendar_id = Column(String(255))
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime)

    user = relationship("User", back_populates="calendar_connections")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "provider_account_email", name="unique_provider_account"),
        CheckConstraint("provider IN ('google', 'microsoft')", name="valid_provider"),
    )
