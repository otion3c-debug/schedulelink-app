from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    timezone: str = "America/New_York"
    booking_slug: str
    subscription_tier: str = "free"
    subscription_status: str = "active"
    bookings_used_this_month: int = 0
    booking_limit: int = 5
    billing_cycle_start: Optional[date] = None
    last_login: Optional[datetime] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    booking_slug: Optional[str] = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str
