from datetime import datetime, timedelta, date, time as dtime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, AvailabilityRule, Booking, CalendarConnection, WidgetCustomization

router = APIRouter(prefix="/public", tags=["public"])


def _slot_overlaps_busy(slot_start: datetime, slot_end: datetime, busy_periods) -> bool:
    for bs, be in busy_periods:
        if slot_start < be and slot_end > bs:
            return True
    return False


@router.get("/users/{user_slug}")
def public_user(user_slug: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.booking_slug == user_slug).first()
    if not user:
        raise HTTPException(404, "User not found")
    widget = db.query(WidgetCustomization).filter(WidgetCustomization.user_id == user.id).first()
    return {
        "full_name": user.full_name,
        "booking_slug": user.booking_slug,
        "timezone": user.timezone,
        "widget": {
            "primary_color": widget.primary_color if widget else "#3B82F6",
            "secondary_color": widget.secondary_color if widget else "#10B981",
            "show_branding": widget.show_branding if widget else True,
            "custom_header_text": widget.custom_header_text if widget else None,
            "custom_footer_text": widget.custom_footer_text if widget else None,
        } if widget else None,
    }


@router.get("/availability/{user_slug}")
async def public_availability(
    user_slug: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    duration_minutes: int = Query(30, ge=15, le=120),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.booking_slug == user_slug).first()
    if not user:
        raise HTTPException(404, "User not found")

    if (end_date - start_date).days > 60:
        raise HTTPException(400, "Date range too large")

    rules_by_day = {}
    for r in db.query(AvailabilityRule).filter(
        AvailabilityRule.user_id == user.id,
        AvailabilityRule.is_active == True,
    ).all():
        rules_by_day.setdefault(r.day_of_week, []).append((r.start_time, r.end_time))

    db_bookings = db.query(Booking).filter(
        Booking.user_id == user.id,
        Booking.status == "confirmed",
        Booking.start_time >= datetime.combine(start_date, dtime.min),
        Booking.start_time <= datetime.combine(end_date + timedelta(days=1), dtime.min),
    ).all()
    busy_periods = [(b.start_time, b.end_time) for b in db_bookings]

    slots = []
    current = start_date
    now = datetime.utcnow()
    while current <= end_date:
        # Python weekday(): Monday=0 ... Sunday=6 (matches our schema)
        windows = rules_by_day.get(current.weekday(), [])
        for win_start, win_end in windows:
            slot_start = datetime.combine(current, win_start)
            window_end = datetime.combine(current, win_end)
            while slot_start + timedelta(minutes=duration_minutes) <= window_end:
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                if slot_end > now and not _slot_overlaps_busy(slot_start, slot_end, busy_periods):
                    slots.append({
                        "start_time": slot_start.isoformat(),
                        "end_time": slot_end.isoformat(),
                        "date": current.isoformat(),
                        "day_name": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][current.weekday()],
                    })
                slot_start += timedelta(minutes=duration_minutes)
        current += timedelta(days=1)

    return {
        "user": {
            "full_name": user.full_name,
            "booking_slug": user.booking_slug,
            "timezone": user.timezone,
        },
        "available_slots": slots,
    }
