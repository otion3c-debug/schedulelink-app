"""Booking management routes (protected)."""

import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..database import get_db, dict_from_row
from ..models import BookingResponse, MessageResponse
from ..services.emailer import send_cancellation_email
from ..services.calendar import delete_calendar_event

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


from typing import List, Optional

@router.get("", response_model=List[BookingResponse])
async def get_bookings(
    current_user: dict = Depends(get_current_user),
    status_filter: str = None
):
    """Get all bookings for the current user."""
    with get_db() as conn:
        query = """
            SELECT * FROM bookings
            WHERE host_id = ?
        """
        params = [current_user["id"]]
        
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        
        query += " ORDER BY booking_time ASC"
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            BookingResponse(
                id=row["id"],
                host_id=row["host_id"],
                client_name=row["client_name"],
                client_email=row["client_email"],
                client_phone=row["client_phone"],
                client_notes=row["client_notes"],
                booking_time=row["booking_time"],
                duration=row["duration"],
                status=row["status"],
                created_at=row["created_at"]
            )
            for row in rows
        ]


@router.delete("/{booking_id}", response_model=MessageResponse)
async def cancel_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a booking (host-initiated)."""
    with get_db() as conn:
        # Get booking
        booking = conn.execute(
            "SELECT * FROM bookings WHERE id = ? AND host_id = ?",
            (booking_id, current_user["id"])
        ).fetchone()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        booking_dict = dict_from_row(booking)
        
        if booking_dict["status"] == "canceled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking already canceled"
            )
        
        # Update status
        conn.execute(
            "UPDATE bookings SET status = 'canceled' WHERE id = ?",
            (booking_id,)
        )
        conn.commit()
        
        # Delete Google Calendar event if exists
        if booking_dict["google_event_id"] and current_user["google_refresh_token"]:
            try:
                await delete_calendar_event(
                    current_user["google_refresh_token"],
                    booking_dict["google_event_id"]
                )
            except Exception:
                pass  # Non-critical
        
        # Send cancellation email to client
        try:
            await send_cancellation_email(
                client_email=booking_dict["client_email"],
                client_name=booking_dict["client_name"],
                host_name=current_user["full_name"],
                booking_time=booking_dict["booking_time"],
                timezone=current_user["timezone"]
            )
        except Exception:
            pass  # Non-critical
        
        return MessageResponse(message="Booking canceled successfully")


@router.get("/cancel/{token}", response_model=MessageResponse)
async def cancel_booking_by_token(token: str):
    """Cancel a booking using cancellation token (from email link)."""
    with get_db() as conn:
        booking = conn.execute(
            "SELECT * FROM bookings WHERE cancellation_token = ?",
            (token,)
        ).fetchone()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid cancellation link"
            )
        
        booking_dict = dict_from_row(booking)
        
        if booking_dict["status"] == "canceled":
            return MessageResponse(message="This booking has already been canceled")
        
        # Get host info
        host = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (booking_dict["host_id"],)
        ).fetchone()
        host_dict = dict_from_row(host)
        
        # Update status
        conn.execute(
            "UPDATE bookings SET status = 'canceled' WHERE id = ?",
            (booking_dict["id"],)
        )
        conn.commit()
        
        # Delete Google Calendar event if exists
        if booking_dict["google_event_id"] and host_dict["google_refresh_token"]:
            try:
                await delete_calendar_event(
                    host_dict["google_refresh_token"],
                    booking_dict["google_event_id"]
                )
            except Exception:
                pass  # Non-critical
        
        # Send notification to host
        try:
            from ..services.emailer import send_cancellation_notification_to_host
            await send_cancellation_notification_to_host(
                host_email=host_dict["email"],
                host_name=host_dict["full_name"],
                client_name=booking_dict["client_name"],
                booking_time=booking_dict["booking_time"],
                timezone=host_dict["timezone"]
            )
        except Exception:
            pass  # Non-critical
        
        return MessageResponse(message="Booking canceled successfully")
