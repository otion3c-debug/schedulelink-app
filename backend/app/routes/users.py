"""User settings routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..database import get_db, dict_from_row
from ..models import (
    UserProfile, UserUpdate, WorkingHoursResponse, 
    WorkingHoursUpdate, WorkingHourDay
)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's full profile."""
    return UserProfile(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        username=current_user["username"],
        timezone=current_user["timezone"],
        meeting_duration=current_user["meeting_duration"],
        buffer_minutes=current_user["buffer_minutes"],
        subscription_status=current_user["subscription_status"],
        google_connected=current_user["google_refresh_token"] is not None,
        created_at=current_user["created_at"]
    )


@router.put("/me", response_model=UserProfile)
async def update_profile(
    data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update current user's profile."""
    updates = []
    params = []
    
    if data.full_name is not None:
        updates.append("full_name = ?")
        params.append(data.full_name)
    
    if data.timezone is not None:
        updates.append("timezone = ?")
        params.append(data.timezone)
    
    if data.meeting_duration is not None:
        updates.append("meeting_duration = ?")
        params.append(data.meeting_duration)
    
    if data.buffer_minutes is not None:
        updates.append("buffer_minutes = ?")
        params.append(data.buffer_minutes)
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    params.append(current_user["id"])
    
    with get_db() as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
        
        # Fetch updated user
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (current_user["id"],)
        ).fetchone()
        user_dict = dict_from_row(user)
        
        return UserProfile(
            id=user_dict["id"],
            email=user_dict["email"],
            full_name=user_dict["full_name"],
            username=user_dict["username"],
            timezone=user_dict["timezone"],
            meeting_duration=user_dict["meeting_duration"],
            buffer_minutes=user_dict["buffer_minutes"],
            subscription_status=user_dict["subscription_status"],
            google_connected=user_dict["google_refresh_token"] is not None,
            created_at=user_dict["created_at"]
        )


@router.get("/working-hours", response_model=WorkingHoursResponse)
async def get_working_hours(current_user: dict = Depends(get_current_user)):
    """Get current user's working hours."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT day_of_week, enabled, start_time, end_time
            FROM working_hours
            WHERE user_id = ?
            ORDER BY day_of_week
            """,
            (current_user["id"],)
        ).fetchall()
        
        hours = [
            WorkingHourDay(
                day_of_week=row["day_of_week"],
                enabled=bool(row["enabled"]),
                start_time=row["start_time"],
                end_time=row["end_time"]
            )
            for row in rows
        ]
        
        return WorkingHoursResponse(hours=hours)


@router.put("/working-hours", response_model=WorkingHoursResponse)
async def update_working_hours(
    data: WorkingHoursUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update current user's working hours."""
    with get_db() as conn:
        for hour in data.hours:
            # Validate time format
            if hour.start_time >= hour.end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"End time must be after start time for day {hour.day_of_week}"
                )
            
            conn.execute(
                """
                UPDATE working_hours
                SET enabled = ?, start_time = ?, end_time = ?
                WHERE user_id = ? AND day_of_week = ?
                """,
                (
                    1 if hour.enabled else 0,
                    hour.start_time,
                    hour.end_time,
                    current_user["id"],
                    hour.day_of_week
                )
            )
        
        conn.commit()
        
        # Fetch updated hours
        rows = conn.execute(
            """
            SELECT day_of_week, enabled, start_time, end_time
            FROM working_hours
            WHERE user_id = ?
            ORDER BY day_of_week
            """,
            (current_user["id"],)
        ).fetchall()
        
        hours = [
            WorkingHourDay(
                day_of_week=row["day_of_week"],
                enabled=bool(row["enabled"]),
                start_time=row["start_time"],
                end_time=row["end_time"]
            )
            for row in rows
        ]
        
        return WorkingHoursResponse(hours=hours)
