"""Pydantic models for request/response validation."""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
import re

# ============== Auth Models ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    full_name: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', v):
            raise ValueError('Username must be lowercase letters, numbers, and hyphens only')
        if len(v) < 2 or len(v) > 30:
            raise ValueError('Username must be 2-30 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    timezone: str
    meeting_duration: int
    buffer_time: int
    is_paid: bool
    google_connected: bool
    
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ============== Working Hours Models ==============

class WorkingHoursUpdate(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str   # "09:00"
    end_time: str     # "17:00"
    is_enabled: bool

class WorkingHoursResponse(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    is_enabled: bool

# ============== Booking Models ==============

class BookingCreate(BaseModel):
    client_name: str
    client_email: EmailStr
    client_phone: Optional[str] = None
    start_time: str  # ISO format
    notes: Optional[str] = None

class BookingResponse(BaseModel):
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
    start: str
    end: str

class DayAvailability(BaseModel):
    date: str
    slots: List[AvailableSlot]

# ============== Settings Models ==============

class SettingsUpdate(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    meeting_duration: Optional[int] = None
    buffer_time: Optional[int] = None
    google_calendar_id: Optional[str] = None

# ============== Public Profile ==============

class PublicProfile(BaseModel):
    username: str
    full_name: Optional[str]
    meeting_duration: int
    timezone: str
