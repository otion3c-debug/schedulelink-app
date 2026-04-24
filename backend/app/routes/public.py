"""Public booking routes (no auth required)."""

import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, status

from ..database import get_db, dict_from_row
from ..models import (
    UserPublic, AvailabilityResponse, AvailabilitySlot,
    BookingCreate, BookingResponse, MessageResponse
)
from ..config import get_settings
from ..services.emailer import send_booking_confirmation_to_client, send_booking_notification_to_host
from ..services.calendar import create_calendar_event

router = APIRouter(prefix="/api/public", tags=["public"])


from typing import List

def get_available_slots(
    user_id: int,
    date_str: str,
    duration: int,
    buffer: int,
    timezone: str,
    conn
) -> List[AvailabilitySlot]:
    """Calculate available time slots for a given date."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = target_date.weekday()
    
    # Get working hours for this day
    working_hours = conn.execute(
        """
        SELECT * FROM working_hours
        WHERE user_id = ? AND day_of_week = ? AND enabled = 1
        """,
        (user_id, day_of_week)
    ).fetchone()
    
    if not working_hours:
        return []  # Not a working day
    
    wh = dict_from_row(working_hours)
    
    # Parse working hours
    start_hour, start_min = map(int, wh["start_time"].split(":"))
    end_hour, end_min = map(int, wh["end_time"].split(":"))
    
    # Create timezone-aware start/end times
    tz = ZoneInfo(timezone)
    work_start = datetime(
        target_date.year, target_date.month, target_date.day,
        start_hour, start_min, tzinfo=tz
    )
    work_end = datetime(
        target_date.year, target_date.month, target_date.day,
        end_hour, end_min, tzinfo=tz
    )
    
    # Get existing bookings for this day
    day_start = datetime(
        target_date.year, target_date.month, target_date.day,
        0, 0, tzinfo=tz
    ).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    day_end = datetime(
        target_date.year, target_date.month, target_date.day,
        23, 59, tzinfo=tz
    ).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    
    existing_bookings = conn.execute(
        """
        SELECT booking_time, duration FROM bookings
        WHERE host_id = ? AND status = 'confirmed'
        AND booking_time >= ? AND booking_time <= ?
        """,
        (user_id, day_start, day_end)
    ).fetchall()
    
    # Convert bookings to datetime objects
    booked_times = []
    for booking in existing_bookings:
        booking_start = datetime.strptime(
            booking["booking_time"], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=ZoneInfo("UTC"))
        booking_end = booking_start + timedelta(minutes=booking["duration"] + buffer)
        booked_times.append((booking_start, booking_end))
    
    # Generate available slots
    slots = []
    current_time = work_start
    slot_duration = timedelta(minutes=duration + buffer)
    
    # Don't show past slots
    now = datetime.now(tz)
    if target_date == now.date():
        # Round up to next 30-minute mark
        if now.minute < 30:
            current_time = max(current_time, now.replace(minute=30, second=0, microsecond=0))
        else:
            current_time = max(current_time, (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0))
    
    while current_time + timedelta(minutes=duration) <= work_end:
        slot_end = current_time + timedelta(minutes=duration)
        slot_with_buffer = current_time + slot_duration
        
        # Check if this slot conflicts with any booking
        is_available = True
        current_utc = current_time.astimezone(ZoneInfo("UTC"))
        slot_end_utc = slot_with_buffer.astimezone(ZoneInfo("UTC"))
        
        for booking_start, booking_end in booked_times:
            # Check for overlap
            if not (slot_end_utc <= booking_start or current_utc >= booking_end):
                is_available = False
                break
        
        if is_available:
            slots.append(AvailabilitySlot(
                time=current_time.strftime("%H:%M"),
                datetime_utc=current_utc.strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        # Move to next slot (30-minute increments)
        current_time += timedelta(minutes=30)
    
    return slots


@router.get("/{username}", response_model=UserPublic)
async def get_host_info(username: str):
    """Get public info for a host's booking page."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT full_name, username, timezone, meeting_duration FROM users WHERE username = ?",
            (username.lower(),)
        ).fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_dict = dict_from_row(user)
        return UserPublic(**user_dict)


@router.get("/{username}/availability", response_model=AvailabilityResponse)
async def get_availability(username: str, date: str):
    """Get available time slots for a specific date."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.lower(),)
        ).fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_dict = dict_from_row(user)
        
        slots = get_available_slots(
            user_id=user_dict["id"],
            date_str=date,
            duration=user_dict["meeting_duration"],
            buffer=user_dict["buffer_minutes"],
            timezone=user_dict["timezone"],
            conn=conn
        )
        
        return AvailabilityResponse(
            date=date,
            slots=slots,
            timezone=user_dict["timezone"]
        )


@router.post("/{username}/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(username: str, data: BookingCreate):
    """Create a new booking (public endpoint)."""
    settings = get_settings()
    
    with get_db() as conn:
        # Get host
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.lower(),)
        ).fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_dict = dict_from_row(user)
        
        # Check booking limit for free users
        if user_dict["subscription_status"] == "free":
            # Count bookings this month
            now = datetime.utcnow()
            month_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d %H:%M:%S")
            
            booking_count = conn.execute(
                """
                SELECT COUNT(*) as count FROM bookings
                WHERE host_id = ? AND created_at >= ? AND status = 'confirmed'
                """,
                (user_dict["id"], month_start)
            ).fetchone()["count"]
            
            if booking_count >= settings.free_bookings_per_month:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="This user has reached their free booking limit. Please ask them to upgrade their account."
                )
        
        # Format booking time for database
        booking_time_utc = data.booking_time.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
        
        # Use IMMEDIATE transaction for conflict prevention
        conn.execute("BEGIN IMMEDIATE")
        
        try:
            # Check for conflicts (same time slot)
            # A conflict exists if the new booking overlaps with any existing booking
            existing = conn.execute(
                """
                SELECT id FROM bookings
                WHERE host_id = ? AND status = 'confirmed'
                AND booking_time = ?
                """,
                (user_dict["id"], booking_time_utc)
            ).fetchone()
            
            if existing:
                conn.execute("ROLLBACK")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This time slot is no longer available. Please select another time."
                )
            
            # Generate cancellation token
            cancellation_token = secrets.token_urlsafe(32)
            
            # Insert booking
            cursor = conn.execute(
                """
                INSERT INTO bookings (
                    host_id, client_name, client_email, client_phone,
                    client_notes, booking_time, duration, cancellation_token
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_dict["id"],
                    data.client_name,
                    data.client_email,
                    data.client_phone,
                    data.client_notes,
                    booking_time_utc,
                    user_dict["meeting_duration"],
                    cancellation_token
                )
            )
            booking_id = cursor.lastrowid
            
            conn.execute("COMMIT")
            
        except HTTPException:
            raise
        except Exception as e:
            conn.execute("ROLLBACK")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create booking"
            )
        
        # Fetch created booking
        booking = conn.execute(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        ).fetchone()
        booking_dict = dict_from_row(booking)
        
        # Create Google Calendar event if connected
        google_event_id = None
        if user_dict["google_refresh_token"]:
            try:
                google_event_id = await create_calendar_event(
                    refresh_token=user_dict["google_refresh_token"],
                    summary=f"Meeting with {data.client_name}",
                    description=f"Client: {data.client_name}\nEmail: {data.client_email}\nPhone: {data.client_phone or 'N/A'}\nNotes: {data.client_notes or 'N/A'}",
                    start_time=data.booking_time,
                    duration_minutes=user_dict["meeting_duration"],
                    timezone=user_dict["timezone"]
                )
                
                if google_event_id:
                    conn.execute(
                        "UPDATE bookings SET google_event_id = ? WHERE id = ?",
                        (google_event_id, booking_id)
                    )
                    conn.commit()
            except Exception as e:
                # Non-critical, log and continue
                print(f"Failed to create Google Calendar event: {e}")
        
        # Send confirmation emails
        cancellation_url = f"{settings.app_url}/api/bookings/cancel/{cancellation_token}"
        
        try:
            await send_booking_confirmation_to_client(
                client_email=data.client_email,
                client_name=data.client_name,
                host_name=user_dict["full_name"],
                booking_time=booking_time_utc,
                duration=user_dict["meeting_duration"],
                timezone=user_dict["timezone"],
                cancellation_url=cancellation_url
            )
        except Exception as e:
            print(f"Failed to send client confirmation email: {e}")
        
        try:
            await send_booking_notification_to_host(
                host_email=user_dict["email"],
                host_name=user_dict["full_name"],
                client_name=data.client_name,
                client_email=data.client_email,
                client_phone=data.client_phone,
                client_notes=data.client_notes,
                booking_time=booking_time_utc,
                duration=user_dict["meeting_duration"],
                timezone=user_dict["timezone"]
            )
        except Exception as e:
            print(f"Failed to send host notification email: {e}")
        
        return BookingResponse(
            id=booking_dict["id"],
            host_id=booking_dict["host_id"],
            client_name=booking_dict["client_name"],
            client_email=booking_dict["client_email"],
            client_phone=booking_dict["client_phone"],
            client_notes=booking_dict["client_notes"],
            booking_time=booking_dict["booking_time"],
            duration=booking_dict["duration"],
            status=booking_dict["status"],
            created_at=booking_dict["created_at"]
        )
