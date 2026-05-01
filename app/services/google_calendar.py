"""Google Calendar event creation and conflict checking."""
from datetime import datetime
from typing import List, Tuple
import httpx
from ..config import settings
from ..models import CalendarConnection
from ..security import decrypt_token, encrypt_token
from . import google_oauth

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


async def ensure_fresh_token(connection: CalendarConnection, db) -> str:
    """Refresh token if expired and persist; return decrypted access token."""
    access = decrypt_token(connection.access_token)
    if connection.token_expires_at and connection.token_expires_at <= datetime.utcnow():
        refresh = decrypt_token(connection.refresh_token)
        token_data = await google_oauth.refresh_access_token(refresh)
        access = token_data["access_token"]
        connection.access_token = encrypt_token(access)
        connection.token_expires_at = google_oauth.expires_at_from_response(token_data)
        db.commit()
    return access


async def create_event(connection: CalendarConnection, booking, db) -> dict:
    access = await ensure_fresh_token(connection, db)
    event = {
        "summary": f"Booking with {booking.attendee_name}",
        "description": booking.notes or "",
        "start": {"dateTime": booking.start_time.isoformat(), "timeZone": booking.timezone},
        "end": {"dateTime": booking.end_time.isoformat(), "timeZone": booking.timezone},
        "attendees": [{"email": booking.attendee_email}],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 30},
            ],
        },
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CALENDAR_API_BASE}/calendars/primary/events?sendUpdates=all",
            headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
            json=event,
        )
        resp.raise_for_status()
        return resp.json()


async def delete_event(connection: CalendarConnection, event_id: str, db) -> None:
    access = await ensure_fresh_token(connection, db)
    async with httpx.AsyncClient(timeout=15) as client:
        await client.delete(
            f"{CALENDAR_API_BASE}/calendars/primary/events/{event_id}?sendUpdates=all",
            headers={"Authorization": f"Bearer {access}"},
        )


async def list_busy(connection: CalendarConnection, start: datetime, end: datetime, db) -> List[Tuple[datetime, datetime]]:
    """Return list of (busy_start, busy_end) tuples (UTC) from FreeBusy API."""
    access = await ensure_fresh_token(connection, db)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CALENDAR_API_BASE}/freeBusy",
            headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
            json={
                "timeMin": start.isoformat() + "Z",
                "timeMax": end.isoformat() + "Z",
                "items": [{"id": "primary"}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    busy = []
    for cal in data.get("calendars", {}).values():
        for b in cal.get("busy", []):
            busy.append((
                datetime.fromisoformat(b["start"].replace("Z", "+00:00")).replace(tzinfo=None),
                datetime.fromisoformat(b["end"].replace("Z", "+00:00")).replace(tzinfo=None),
            ))
    return busy
