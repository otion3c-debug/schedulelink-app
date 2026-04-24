"""Google Calendar service."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import httpx

from ..config import get_settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


async def refresh_access_token(refresh_token: str) -> str:
    """Refresh Google access token."""
    settings = get_settings()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to refresh token: {response.text}")
        
        return response.json()["access_token"]


async def create_calendar_event(
    refresh_token: str,
    summary: str,
    description: str,
    start_time: datetime,
    duration_minutes: int,
    timezone: str
) -> str:
    """Create a Google Calendar event and return event ID."""
    access_token = await refresh_access_token(refresh_token)
    
    # Ensure start_time is timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=ZoneInfo(timezone))
    
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": timezone
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": timezone
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60}
            ]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=event
        )
        
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to create event: {response.text}")
        
        return response.json()["id"]


async def delete_calendar_event(refresh_token: str, event_id: str):
    """Delete a Google Calendar event."""
    access_token = await refresh_access_token(refresh_token)
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events/{event_id}",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if response.status_code not in (200, 204):
            raise Exception(f"Failed to delete event: {response.text}")
