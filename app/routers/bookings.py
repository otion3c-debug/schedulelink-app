from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..database import get_db
from ..models import Booking, User, CalendarConnection, AvailabilityRule
from ..schemas.booking import BookingCreate, BookingOut, BookingUpdate, BookingCancel
from ..security import get_current_user
from ..services import google_calendar, microsoft_calendar, email_service
import uuid

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _ensure_quota(user: User):
    today = date.today()
    if user.billing_cycle_start is None:
        user.billing_cycle_start = today
    # Reset monthly counter if cycle has rolled over
    if user.billing_cycle_start <= today - timedelta(days=30):
        user.bookings_used_this_month = 0
        user.billing_cycle_start = today
    if user.subscription_tier == "free" and user.bookings_used_this_month >= (user.booking_limit or 5):
        raise HTTPException(
            status_code=402,
            detail={
                "error": {
                    "code": "BOOKING_LIMIT_REACHED",
                    "message": f"You've reached your monthly booking limit ({user.booking_limit}/{user.booking_limit}). Upgrade to Pro for unlimited bookings.",
                    "details": {
                        "current_tier": user.subscription_tier,
                        "bookings_used": user.bookings_used_this_month,
                        "booking_limit": user.booking_limit,
                    },
                    "upgrade_url": "/dashboard/billing",
                }
            },
        )


def _check_db_conflict(db: Session, user_id, start: datetime, end: datetime, exclude_id=None) -> bool:
    q = db.query(Booking).filter(
        Booking.user_id == user_id,
        Booking.status == "confirmed",
        Booking.start_time < end,
        Booking.end_time > start,
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    return q.first() is not None


@router.get("")
def list_bookings(
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Booking).filter(Booking.user_id == current_user.id)
    if status:
        q = q.filter(Booking.status == status)
    if start_date:
        q = q.filter(Booking.start_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        q = q.filter(Booking.start_time <= datetime.combine(end_date, datetime.max.time()))
    total = q.count()
    rows = q.order_by(Booking.start_time.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "bookings": [BookingOut.model_validate(b).model_dump(mode="json") for b in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("")
async def create_booking(body: BookingCreate, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.booking_slug == body.user_slug).first()
    if not user:
        raise HTTPException(404, "User not found")

    _ensure_quota(user)

    start_naive = body.start_time.replace(tzinfo=None) if body.start_time.tzinfo else body.start_time
    end_naive = start_naive + timedelta(minutes=body.duration_minutes)

    if _check_db_conflict(db, user.id, start_naive, end_naive):
        raise HTTPException(409, "Time slot already booked")

    booking = Booking(
        user_id=user.id,
        attendee_name=body.attendee_name,
        attendee_email=body.attendee_email,
        attendee_phone=body.attendee_phone,
        start_time=start_naive,
        end_time=end_naive,
        duration_minutes=body.duration_minutes,
        timezone=body.timezone,
        notes=body.notes,
        status="confirmed",
    )
    db.add(booking)
    db.flush()

    primary = db.query(CalendarConnection).filter(
        CalendarConnection.user_id == user.id,
        CalendarConnection.is_primary == True,
        CalendarConnection.is_active == True,
    ).first()

    calendar_event_created = False
    if primary and primary.provider == "google":
        try:
            event = await google_calendar.create_event(primary, booking, db)
            booking.calendar_event_id = event.get("id")
            booking.calendar_provider = "google"
            calendar_event_created = True
        except Exception as e:
            # Don't fail the booking if calendar push fails — log and continue.
            import logging; logging.getLogger(__name__).error(f"Calendar event create failed: {e}")
    elif primary and primary.provider == "microsoft":
        try:
            event = await microsoft_calendar.create_event(primary, booking, db)
            booking.calendar_event_id = event.get("id")
            booking.calendar_provider = "microsoft"
            calendar_event_created = True
        except Exception as e:
            import logging; logging.getLogger(__name__).error(f"Microsoft calendar event create failed: {e}")

    user.bookings_used_this_month = (user.bookings_used_this_month or 0) + 1
    db.commit()
    db.refresh(booking)

    bg_tasks.add_task(email_service.send_booking_confirmation, booking)
    bg_tasks.add_task(email_service.send_owner_notification, booking, user.email, user.display_name or user.email)

    return {
        "id": str(booking.id),
        "booking_url": f"/booking/{booking.id}",
        "calendar_event_created": calendar_event_created,
        "confirmation_email_sent": True,
        "owner_notified": True,
    }


@router.get("/{booking_id}")
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = db.query(Booking).filter(
        Booking.id == uuid.UUID(booking_id),
        Booking.user_id == current_user.id,
    ).first()
    if not b:
        raise HTTPException(404, "Booking not found")
    return BookingOut.model_validate(b).model_dump(mode="json")


@router.patch("/{booking_id}")
async def update_booking(
    booking_id: str,
    body: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = db.query(Booking).filter(
        Booking.id == uuid.UUID(booking_id),
        Booking.user_id == current_user.id,
    ).first()
    if not b:
        raise HTTPException(404, "Booking not found")
    if body.start_time:
        new_start = body.start_time.replace(tzinfo=None) if body.start_time.tzinfo else body.start_time
        new_end = new_start + timedelta(minutes=b.duration_minutes)
        if _check_db_conflict(db, current_user.id, new_start, new_end, exclude_id=b.id):
            raise HTTPException(409, "Time slot already booked")
        b.start_time = new_start
        b.end_time = new_end
    if body.notes is not None:
        b.notes = body.notes
    db.commit()
    db.refresh(b)
    return BookingOut.model_validate(b).model_dump(mode="json")


@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: str,
    body: BookingCancel = BookingCancel(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = db.query(Booking).filter(
        Booking.id == uuid.UUID(booking_id),
        Booking.user_id == current_user.id,
    ).first()
    if not b:
        raise HTTPException(404, "Booking not found")
    b.status = "cancelled"
    b.cancelled_at = datetime.utcnow()
    b.cancellation_reason = body.cancellation_reason

    if b.calendar_event_id and b.calendar_provider in ("google", "microsoft"):
        primary = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == current_user.id,
            CalendarConnection.is_primary == True,
        ).first()
        if primary:
            try:
                if b.calendar_provider == "google":
                    await google_calendar.delete_event(primary, b.calendar_event_id, db)
                elif b.calendar_provider == "microsoft":
                    await microsoft_calendar.delete_event(primary, b.calendar_event_id, db)
            except Exception:
                pass
    db.commit()
    return {"success": True}
