"""Microsoft Graph (Outlook) calendar event creation and conflict checking."""
from datetime import datetime
from typing import List, Tuple
import httpx
from ..models import CalendarConnection
from ..security import decrypt_token, encrypt_token
from . import microsoft_oauth

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


async def ensure_fresh_token(connection: CalendarConnection, db) -> str:
    """Refresh token if expired and persist; return decrypted access token."""
    access = decrypt_token(connection.access_token)
    if connection.token_expires_at and connection.token_expires_at <= datetime.utcnow():
        refresh = decrypt_token(connection.refresh_token)
        token_data = await microsoft_oauth.refresh_access_token(refresh)
        access = token_data["access_token"]
        connection.access_token = encrypt_token(access)
        # Microsoft may rotate refresh tokens — persist the new one if returned.
        if token_data.get("refresh_token"):
            connection.refresh_token = encrypt_token(token_data["refresh_token"])
        connection.token_expires_at = microsoft_oauth.expires_at_from_response(token_data)
        db.commit()
    return access


async def create_event(connection: CalendarConnection, booking, db) -> dict:
    """Create an Outlook calendar event for the booking. Returns Graph response."""
    access = await ensure_fresh_token(connection, db)
    event = {
        "subject": f"Booking with {booking.attendee_name}",
        "body": {
            "contentType": "text",
            "content": booking.notes or "",
        },
        "start": {
            "dateTime": booking.start_time.isoformat(),
            "timeZone": booking.timezone,
        },
        "end": {
            "dateTime": booking.end_time.isoformat(),
            "timeZone": booking.timezone,
        },
        "attendees": [
            {
                "emailAddress": {
                    "address": booking.attendee_email,
                    "name": booking.attendee_name,
                },
                "type": "required",
            }
        ],
        "reminderMinutesBeforeStart": 30,
        "isReminderOn": True,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{GRAPH_API_BASE}/me/events",
            headers={
                "Authorization": f"Bearer {access}",
                "Content-Type": "application/json",
            },
            json=event,
        )
        resp.raise_for_status()
        return resp.json()


async def update_event(connection: CalendarConnection, event_id: str, booking, db) -> dict:
    """Patch an existing Outlook event with new booking times/notes."""
    access = await ensure_fresh_token(connection, db)
    payload = {
        "subject": f"Booking with {booking.attendee_name}",
        "body": {
            "contentType": "text",
            "content": booking.notes or "",
        },
        "start": {
            "dateTime": booking.start_time.isoformat(),
            "timeZone": booking.timezone,
        },
        "end": {
            "dateTime": booking.end_time.isoformat(),
            "timeZone": booking.timezone,
        },
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{GRAPH_API_BASE}/me/events/{event_id}",
            headers={
                "Authorization": f"Bearer {access}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def delete_event(connection: CalendarConnection, event_id: str, db) -> None:
    access = await ensure_fresh_token(connection, db)
    async with httpx.AsyncClient(timeout=15) as client:
        await client.delete(
            f"{GRAPH_API_BASE}/me/events/{event_id}",
            headers={"Authorization": f"Bearer {access}"},
        )


async def list_busy(
    connection: CalendarConnection, start: datetime, end: datetime, db
) -> List[Tuple[datetime, datetime]]:
    """Return list of (busy_start, busy_end) tuples (UTC) using Graph getSchedule."""
    access = await ensure_fresh_token(connection, db)
    schedule_email = connection.provider_account_email
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{GRAPH_API_BASE}/me/calendar/getSchedule",
            headers={
                "Authorization": f"Bearer {access}",
                "Content-Type": "application/json",
            },
            json={
                "schedules": [schedule_email],
                "startTime": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "endTime": {"dateTime": end.isoformat(), "timeZone": "UTC"},
                "availabilityViewInterval": 30,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    busy: List[Tuple[datetime, datetime]] = []
    for item in data.get("value", []):
        for b in item.get("scheduleItems", []):
            status = b.get("status", "busy")
            if status == "free":
                continue
            busy.append((
                _parse_graph_dt(b["start"]["dateTime"]),
                _parse_graph_dt(b["end"]["dateTime"]),
            ))
    return busy


def _parse_graph_dt(value: str) -> datetime:
    """Graph returns 'YYYY-MM-DDTHH:MM:SS.fffffff' without timezone suffix (already UTC)."""
    cleaned = value.rstrip("Z")
    if "." in cleaned:
        head, frac = cleaned.split(".", 1)
        cleaned = f"{head}.{frac[:6]}"
    return datetime.fromisoformat(cleaned)
