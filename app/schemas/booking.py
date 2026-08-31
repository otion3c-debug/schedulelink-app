from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, model_validator


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

    # Canonical UTC instants. Derived from the stored naive local time + timezone so
    # server components / any client can render correct absolute time regardless of host tz.
    start_time_utc: Optional[datetime] = None
    end_time_utc: Optional[datetime] = None

    @model_validator(mode="after")
    def _attach_utc(self):
        try:
            tz = ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, Exception):
            tz = None
        if tz is not None:
            local = self.start_time if self.start_time.tzinfo is None else self.start_time.replace(tzinfo=None)
            self.start_time_utc = local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
            if self.end_time is not None:
                end_local = self.end_time if self.end_time.tzinfo is None else self.end_time.replace(tzinfo=None)
                self.end_time_utc = end_local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
        elif self.start_time.tzinfo is not None:
            # Already offset-aware (e.g. aware datetime stored): normalize to UTC directly.
            self.start_time_utc = self.start_time.astimezone(ZoneInfo("UTC"))
            if self.end_time is not None:
                self.end_time_utc = self.end_time.astimezone(ZoneInfo("UTC"))
        return self
