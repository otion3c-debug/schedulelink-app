"""Pydantic models for request/response validation.

All API requests and responses are validated through these models.
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
import re


# ============== Auth Models ==============

class UserCreate(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str
    username: str
    full_name: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.lower().strip()
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', v):
            raise ValueError('Username must be lowercase letters, numbers, and hyphens only')
        if len(v) < 2 or len(v) > 30:
            raise ValueError('Username must be 2-30 characters')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response model for user profile."""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    timezone: str
    meeting_duration: int
    buffer_time: int
    is_paid: bool
    subscription_status: str  # 'free', 'pro', 'pro_plus'
    google_connected: bool


class Token(BaseModel):
    """Response model for JWT token."""
    access_token: str
    token_type: str = "bearer"


# ============== Working Hours Models ==============

class WorkingHoursUpdate(BaseModel):
    """Request model for updating working hours."""
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str   # "HH:MM" format
    end_time: str     # "HH:MM" format
    is_enabled: bool
    
    @field_validator('day_of_week')
    @classmethod
    def validate_day(cls, v: int) -> int:
        if v < 0 or v > 6:
            raise ValueError('Day of week must be 0-6 (Monday-Sunday)')
        return v
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r'^\d{2}:\d{2}$', v):
            raise ValueError('Time must be in HH:MM format')
        hours, minutes = map(int, v.split(':'))
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            raise ValueError('Invalid time value')
        return v


class WorkingHoursResponse(BaseModel):
    """Response model for working hours."""
    day_of_week: int
    start_time: str
    end_time: str
    is_enabled: bool


# ============== Booking Models ==============

class BookingCreate(BaseModel):
    """Request model for creating a booking (public endpoint)."""
    client_name: str
    client_email: EmailStr
    client_phone: Optional[str] = None
    start_time: str  # ISO format datetime
    notes: Optional[str] = None
    
    @field_validator('client_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Name must be under 100 characters')
        return v
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 1000:
            raise ValueError('Notes must be under 1000 characters')
        return v.strip() if v else None


class BookingResponse(BaseModel):
    """Response model for booking details."""
    id: int
    client_name: str
    client_email: str
    client_phone: Optional[str]
    start_time: str
    end_time: str
    notes: Optional[str]
    status: str
    created_at: str


class AvailableSlot(BaseModel):
    """Model for an available time slot."""
    start: str
    end: str


class DayAvailability(BaseModel):
    """Model for a day's availability."""
    date: str
    slots: List[AvailableSlot]


# ============== Settings Models ==============

class SettingsUpdate(BaseModel):
    """Request model for updating user settings."""
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    meeting_duration: Optional[int] = None
    buffer_time: Optional[int] = None
    google_calendar_id: Optional[str] = None
    
    @field_validator('meeting_duration')
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in [15, 30, 45, 60, 90, 120]:
            raise ValueError('Meeting duration must be 15, 30, 45, 60, 90, or 120 minutes')
        return v
    
    @field_validator('buffer_time')
    @classmethod
    def validate_buffer(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in [0, 5, 10, 15, 30]:
            raise ValueError('Buffer time must be 0, 5, 10, 15, or 30 minutes')
        return v


# ============== Public Profile ==============

class PublicProfile(BaseModel):
    """Response model for public profile (no auth required)."""
    username: str
    full_name: Optional[str]
    meeting_duration: int
    timezone: str
