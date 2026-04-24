"""Pydantic models for request/response validation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ============== Auth Models ==============

class UserRegister(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")


class UserLogin(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: int
    email: str


# ============== User Models ==============

class UserPublic(BaseModel):
    """Public user information (for booking pages)."""
    full_name: str
    username: str
    timezone: str
    meeting_duration: int


class UserProfile(BaseModel):
    """Full user profile for dashboard."""
    id: int
    email: str
    full_name: str
    username: str
    timezone: str
    meeting_duration: int
    buffer_minutes: int
    subscription_status: str
    google_connected: bool
    created_at: str


class UserUpdate(BaseModel):
    """Update user profile request."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    timezone: Optional[str] = None
    meeting_duration: Optional[int] = Field(None, ge=15, le=180)
    buffer_minutes: Optional[int] = Field(None, ge=0, le=60)


# ============== Working Hours Models ==============

class WorkingHourDay(BaseModel):
    """Single day working hours."""
    day_of_week: int = Field(ge=0, le=6)
    enabled: bool
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")


class WorkingHoursUpdate(BaseModel):
    """Update working hours request."""
    hours: List[WorkingHourDay]


class WorkingHoursResponse(BaseModel):
    """Working hours response."""
    hours: List[WorkingHourDay]


# ============== Booking Models ==============

class BookingCreate(BaseModel):
    """Create booking request (public)."""
    client_name: str = Field(min_length=1, max_length=100)
    client_email: EmailStr
    client_phone: Optional[str] = Field(None, max_length=20)
    client_notes: Optional[str] = Field(None, max_length=500)
    booking_time: datetime


class BookingResponse(BaseModel):
    """Booking response."""
    id: int
    host_id: int
    client_name: str
    client_email: str
    client_phone: Optional[str]
    client_notes: Optional[str]
    booking_time: str
    duration: int
    status: str
    created_at: str


class AvailabilitySlot(BaseModel):
    """Available time slot."""
    time: str
    datetime_utc: str


class AvailabilityResponse(BaseModel):
    """Availability response for a date."""
    date: str
    slots: List[AvailabilitySlot]
    timezone: str


# ============== Stripe Models ==============

class CheckoutSessionResponse(BaseModel):
    """Stripe checkout session response."""
    checkout_url: str


class PortalSessionResponse(BaseModel):
    """Stripe portal session response."""
    portal_url: str


# ============== Google Models ==============

class GoogleAuthResponse(BaseModel):
    """Google OAuth redirect URL."""
    auth_url: str


# ============== General ==============

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
