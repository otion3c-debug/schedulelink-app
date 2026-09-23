from datetime import datetime, timedelta, timezone, date
import json
import logging
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import AvailabilityRule, Booking, CalendarConnection, User
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


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _fmt_time(value) -> str:
    """12-hour clock without locale/platform-specific format codes (%-I is not portable)."""
    hour = value.hour % 12 or 12
    return f"{hour}:{value.minute:02d} {'AM' if value.hour < 12 else 'PM'}"


def _availability_by_day(db: Session, user: User) -> dict:
    """Active availability windows keyed by weekday (0=Monday), matching the schema."""
    by_day: dict = {}
    for r in db.query(AvailabilityRule).filter(
        AvailabilityRule.user_id == user.id,
        AvailabilityRule.is_active == True,
    ).all():
        by_day.setdefault(r.day_of_week, []).append((r.start_time, r.end_time))
    return by_day


def _describe_availability(by_day: dict, tz_name: str) -> str:
    if not by_day:
        return "no bookable hours are configured"
    parts = []
    for day in sorted(by_day):
        windows = ", ".join(f"{_fmt_time(s)}-{_fmt_time(e)}" for s, e in sorted(by_day[day]))
        label = DAY_NAMES[day] if 0 <= day < 7 else str(day)
        parts.append(f"{label} {windows}")
    return "; ".join(parts) + f" ({tz_name})"


def _slot_within_availability(by_day: dict, local_start: datetime, local_end: datetime) -> bool:
    """True when [local_start, local_end) fits entirely inside one window, same day.

    Mirrors the loop in /public/availability: windows are naive local wall-clock
    times in the host's own timezone, weekday 0=Monday.
    """
    if local_end.date() != local_start.date():
        return False
    for win_start, win_end in by_day.get(local_start.weekday(), []):
        if win_start <= local_start.time() and local_end.time() <= win_end:
            return True
    return False


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

    end_utc = start_utc + timedelta(minutes=duration)

    attendee_email = _clean_str(params.get("attendee_email"), max_len=255)
    attendee_phone = _clean_str(params.get("attendee_phone"), max_len=50)
    tz = _clean_str(params.get("timezone"), max_len=50) or "UTC"
    notes = _clean_str(params.get("notes"), max_len=2000)
    service_type = _clean_str(params.get("service_type"), max_len=100)
    if service_type:
        notes = f"Service: {service_type}\n{notes}" if notes else f"Service: {service_type}"

    booking_slug = settings.VAPI_BOOKING_SLUG or "eric"
    user = db.query(User).filter(User.booking_slug == booking_slug).first()
    if not user:
        # Self-hosted Vapi deployments often leave VAPI_BOOKING_SLUG pointing at a slug
        # that has since been renamed (or was guessed at authoring time). If this
        # deployment holds exactly one account, that account is unambiguously the host.
        # With more than one account the slug must be correct — refuse rather than
        # risk booking onto the wrong person's calendar.
        candidates = db.query(User).order_by(User.created_at.asc()).limit(2).all()
        if len(candidates) == 1:
            user = candidates[0]
            logger.warning(
                f"Vapi webhook: configured booking slug '{booking_slug}' not found — "
                f"falling back to the only account on this deployment ('{user.booking_slug}'). "
                f"Set VAPI_BOOKING_SLUG to fix."
            )
        else:
            known = [u.booking_slug for u in db.query(User).limit(10).all()]
            logger.error(
                f"Vapi webhook: configured booking slug '{booking_slug}' not found and "
                f"this deployment has {len(candidates)}+ accounts — cannot infer the host. "
                f"Known slugs: {known}"
            )
            return _vapi_result(tool_call_id, "Sorry, the booking host isn't configured yet — please try again later.")

    # Enforce the host's real availability windows. Vapi only knows the hours we
    # describe in prose, so without this the phone agent books weekends and the
    # middle of the night while the public booking page would refuse them.
    host_tz_name = user.timezone or "UTC"
    try:
        host_zone = ZoneInfo(host_tz_name)
    except Exception:
        host_zone = timezone.utc
    by_day = _availability_by_day(db, user)
    local_start = start_utc.replace(tzinfo=timezone.utc).astimezone(host_zone).replace(tzinfo=None)
    local_end = end_utc.replace(tzinfo=timezone.utc).astimezone(host_zone).replace(tzinfo=None)
    if not _slot_within_availability(by_day, local_start, local_end):
        windows = _describe_availability(by_day, host_tz_name)
        logger.info(
            f"Vapi webhook: {start_utc} UTC is outside host availability for user "
            f"{user.id} — windows: {windows}"
        )
        return _vapi_result(
            tool_call_id,
            f"That time is outside the host's booking hours. The host books: {windows}. "
            f"Apologize briefly, read those windows to the caller, and offer one of them. "
            f"Do not offer or book anything outside those windows.",
        )

    _refresh_quota(user)
    if _quota_exceeded(user):
        logger.info(f"Vapi webhook: quota exceeded for user {user.id}")
        return _vapi_result(
            tool_call_id,
            "Sorry, the booking calendar has reached its monthly limit. Please try again next month.",
        )

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
            email_service.send_booking_confirmation(
                booking.attendee_email,
                booking.attendee_name,
                booking.user.full_name or "your host",
                booking.start_time,
                booking.timezone,
                booking.duration_minutes,
                booking.notes,
                booking.id)
        except Exception as e:
            logger.warning(f"Vapi webhook: failed to send confirmation email: {e}")
    try:
        email_service.send_owner_notification(
            booking.user.email,
            booking.user.full_name or booking.user.email,
            booking.attendee_name,
            booking.start_time,
            booking.timezone,
            booking.duration_minutes,
            booking.attendee_email,
            booking.attendee_phone,
            booking.notes)
    except Exception as e:
        logger.warning(f"Vapi webhook: failed to send owner notification: {e}")

    local = start_utc.replace(tzinfo=timezone.utc).astimezone(host_zone)
    day_phrase = f"{local.strftime('%A, %B')} {local.day}"
    time_phrase = _fmt_time(local)
    extra = " A calendar event was created." if calendar_event_created else ""
    text = (
        f"Booked a {duration}-minute meeting for {attendee_name} on "
        f"{day_phrase} at {time_phrase} ({host_tz_name}).{extra} "
        f'Confirm it to the caller by saying exactly: "You are all set for '
        f'{day_phrase} at {time_phrase}." '
        f"Never state a date, day of the week, or time that is not in this message."
    )
    logger.info(f"Vapi webhook: created booking {booking.id} for user {user.id}")
    return _vapi_result(tool_call_id, text)
