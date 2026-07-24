from datetime import datetime, timedelta, timezone, date
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Booking, CalendarConnection, User
from ..services import email_service, google_calendar, microsoft_calendar

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vapi", tags=["vapi"])

ALLOWED_DURATIONS = {15, 30, 45, 60, 90, 120}
MAX_FUTURE_DAYS = 90
NO_EMAIL_PLACEHOLDER = "no-email@vapi.local"


def _vapi_result(tool_call_id: str, text: str) -> dict:
    return {"results": [{"toolCallId": tool_call_id, "result": text}]}


def _extract_call(payload: Optional[dict]) -> tuple[str, dict]:
    """Return (toolCallId, parameters) from a Vapi webhook body.

    Supports both the modern `message.toolCalls[]` shape and the legacy
    `message.functionCall` shape.
    """
    msg = (payload or {}).get("message") or {}
    tool_calls = msg.get("toolCalls") or []
    if tool_calls:
        tc = tool_calls[0] or {}
        tc_id = tc.get("id") or ""
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (ValueError, TypeError):
                args = {}
        return tc_id, args or {}
    fc = msg.get("functionCall") or {}
    return "", fc.get("parameters") or {}


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _to_naive_utc(dt: datetime) -> datetime:
    """Convert tz-aware datetimes to naive UTC; treat naive inputs as already UTC."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _clean_str(value: Any, max_len: int) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    v = value.strip()
    if not v:
        return None
    return v[:max_len]


def _has_db_conflict(db: Session, user_id, start: datetime, end: datetime) -> bool:
    return db.query(Booking).filter(
        Booking.user_id == user_id,
        Booking.status == "confirmed",
        Booking.start_time < end,
        Booking.end_time > start,
    ).first() is not None


def _refresh_quota(user: User) -> None:
    today = date.today()
    if user.billing_cycle_start is None:
        user.billing_cycle_start = today
    if user.billing_cycle_start <= today - timedelta(days=30):
        user.bookings_used_this_month = 0
        user.billing_cycle_start = today


def _quota_exceeded(user: User) -> bool:
    return (
        user.subscription_tier == "free"
        and (user.bookings_used_this_month or 0) >= (user.booking_limit or 5)
    )


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    x_vapi_secret: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    try:
        payload = await request.json()
    except Exception as e:
        logger.warning(f"Vapi webhook: invalid JSON body: {e}")
        return _vapi_result("", "Sorry, I couldn't process that request — the payload was invalid.")

    tool_call_id, params = _extract_call(payload)

    expected_secret = settings.VAPI_WEBHOOK_SECRET
    if expected_secret and x_vapi_secret != expected_secret:
        logger.warning("Vapi webhook: rejected request — missing or invalid X-Vapi-Secret header")
        return _vapi_result(tool_call_id, "Sorry, this booking request could not be authorized.")

    attendee_name = _clean_str(params.get("attendee_name"), max_len=100)
    if not attendee_name or len(attendee_name) < 2:
        return _vapi_result(tool_call_id, "I need the attendee's full name (at least 2 characters) to book this meeting.")

    start_dt = _parse_iso_datetime(params.get("start_time"))
    if start_dt is None:
        return _vapi_result(
            tool_call_id,
            "I couldn't understand the start time. Please provide an ISO 8601 datetime (e.g. 2026-06-01T14:00:00-04:00).",
        )

    start_utc = _to_naive_utc(start_dt)
    now_utc = datetime.utcnow()
    if start_utc < now_utc - timedelta(minutes=5):
        return _vapi_result(tool_call_id, "That start time is in the past — please pick a future time.")
    if start_utc > now_utc + timedelta(days=MAX_FUTURE_DAYS):
        return _vapi_result(
            tool_call_id,
            f"I can only book up to {MAX_FUTURE_DAYS} days in advance.",
        )

    duration_raw = params.get("duration_minutes", 30)
    try:
        duration = int(duration_raw)
    except (TypeError, ValueError):
        return _vapi_result(tool_call_id, "The duration must be a number of minutes.")
    if duration not in ALLOWED_DURATIONS:
        return _vapi_result(
            tool_call_id,
            f"Duration must be one of {sorted(ALLOWED_DURATIONS)} minutes.",
        )

    attendee_email = _clean_str(params.get("attendee_email"), max_len=255)
    attendee_phone = _clean_str(params.get("attendee_phone"), max_len=50)
    tz = _clean_str(params.get("timezone"), max_len=50) or "UTC"
    notes = _clean_str(params.get("notes"), max_len=2000)
    service_type = _clean_str(params.get("service_type"), max_len=100)
    if service_type:
        notes = f"Service: {service_type}\n{notes}" if notes else f"Service: {service_type}"

    booking_slug = settings.VAPI_BOOKING_SLUG or "eric-hunt"
    user = db.query(User).filter(User.booking_slug == booking_slug).first()
    if not user:
        logger.error(f"Vapi webhook: configured booking slug '{booking_slug}' not found")
        return _vapi_result(tool_call_id, "Sorry, the booking host isn't configured yet — please try again later.")

    _refresh_quota(user)
    if _quota_exceeded(user):
        logger.info(f"Vapi webhook: quota exceeded for user {user.id}")
        return _vapi_result(
            tool_call_id,
            "Sorry, the booking calendar has reached its monthly limit. Please try again next month.",
        )

    end_utc = start_utc + timedelta(minutes=duration)
    if _has_db_conflict(db, user.id, start_utc, end_utc):
        return _vapi_result(tool_call_id, "That time slot is already booked. Could you try another time?")

    booking = Booking(
        user_id=user.id,
        attendee_name=attendee_name,
        attendee_email=attendee_email or NO_EMAIL_PLACEHOLDER,
        attendee_phone=attendee_phone,
        start_time=start_utc,
        end_time=end_utc,
        duration_minutes=duration,
        timezone=tz,
        notes=notes,
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
            logger.error(f"Vapi webhook: Google calendar create failed: {e}")
    elif primary and primary.provider == "microsoft":
        try:
            event = await microsoft_calendar.create_event(primary, booking, db)
            booking.calendar_event_id = event.get("id")
            booking.calendar_provider = "microsoft"
            calendar_event_created = True
        except Exception as e:
            logger.error(f"Vapi webhook: Microsoft calendar create failed: {e}")

    user.bookings_used_this_month = (user.bookings_used_this_month or 0) + 1

    try:
        db.commit()
        db.refresh(booking)
    except Exception as e:
        logger.exception(f"Vapi webhook: commit failed: {e}")
        db.rollback()
        return _vapi_result(tool_call_id, "Sorry, something went wrong saving the booking. Please try again.")

    if attendee_email:
        try:
            email_service.send_booking_confirmation(booking)
        except Exception as e:
            logger.warning(f"Vapi webhook: failed to send confirmation email: {e}")
    try:
        email_service.send_owner_notification(booking, booking.user.email, booking.user.display_name or booking.user.email)
    except Exception as e:
        logger.warning(f"Vapi webhook: failed to send owner notification: {e}")

    pretty_start = start_utc.strftime("%A, %B %d at %H:%M UTC")
    extra = " A calendar event was created." if calendar_event_created else ""
    text = f"Booked a {duration}-minute meeting for {attendee_name} on {pretty_start}.{extra}"
    logger.info(f"Vapi webhook: created booking {booking.id} for user {user.id}")
    return _vapi_result(tool_call_id, text)
