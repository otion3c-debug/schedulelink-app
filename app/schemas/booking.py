from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator


class BookingCreate(BaseModel):
    user_slug: str
    attendee_name: str
    attendee_email: EmailStr
    attendee_phone: Optional[str] = None
    start_time: datetime
    timezone: str
    duration_minutes: int = 30
    notes: Optional[str] = None

    @field_validator("attendee_name")
    @classmethod
    def _check_name(cls, v):
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Name must be 2-100 characters")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def _check_duration(cls, v):
        if v not in [15, 30, 45, 60, 90, 120]:
            raise ValueError("Invalid duration")
        return v

    @field_validator("start_time")
    @classmethod
    def _check_start(cls, v):
        # Compare naively in UTC; clients send local-aware ISO strings, but pydantic returns datetime as-is.
        now = datetime.utcnow()
        cmp_v = v.replace(tzinfo=None) if v.tzinfo else v
        if cmp_v < now - timedelta(minutes=5):
            raise ValueError("Cannot book in the past")
        if cmp_v > now + timedelta(days=90):
            raise ValueError("Cannot book more than 90 days in advance")
        return v


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    notes: Optional[str] = None


class BookingCancel(BaseModel):
    cancellation_reason: Optional[str] = None


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attendee_name: str
    attendee_email: str
    attendee_phone: Optional[str] = None
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    timezone: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
