"""Google Calendar API integration.

Handles:
- OAuth2 authentication flow
- Calendar event creation/deletion
- Free/busy queries for availability
"""
import os
import json
import urllib.request
import urllib.parse
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/api/auth/google/callback")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]


def is_configured() -> bool:
    """Check if Google Calendar API is configured."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def get_google_auth_url(state: str = "") -> str:
    """Generate Google OAuth authorization URL."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }).encode()
    
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh an expired access token."""
    data = urllib.parse.urlencode({
        "refresh_token": refresh_token,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }).encode()
    
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def get_freebusy(
    access_token: str, 
    calendar_id: str, 
    time_min: str, 
    time_max: str
) -> List[Dict[str, str]]:
    """Get free/busy information from Google Calendar.
    
    Returns list of busy time periods: [{"start": "...", "end": "..."}]
    """
    body = json.dumps({
        "timeMin": time_min,
        "timeMax": time_max,
        "items": [{"id": calendar_id}]
    }).encode()
    
    req = urllib.request.Request(
        "https://www.googleapis.com/calendar/v3/freeBusy",
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            calendars = data.get("calendars", {})
            calendar_data = calendars.get(calendar_id, {})
            return calendar_data.get("busy", [])
    except urllib.error.HTTPError as e:
        print(f"[Calendar] Error fetching freebusy: {e.code} - {e.reason}")
        return []
    except Exception as e:
        print(f"[Calendar] Error fetching freebusy: {e}")
        return []


def create_calendar_event(
    access_token: str,
    calendar_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    attendee_email: str = "",
    timezone: str = "America/New_York"
) -> Optional[str]:
    """Create a calendar event and return the event ID."""
    # Ensure datetime has proper format
    def format_datetime(dt: str) -> str:
        if dt.endswith('Z') or '+' in dt:
            return dt
        # Add seconds if missing
        if len(dt) == 16:  # "2024-01-01T10:00"
            return dt + ":00"
        return dt
    
    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": format_datetime(start_time),
            "timeZone": timezone
        },
        "end": {
            "dateTime": format_datetime(end_time),
            "timeZone": timezone
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 60},
                {"method": "popup", "minutes": 15}
            ]
        }
    }
    
    if attendee_email:
        event["attendees"] = [{"email": attendee_email}]
    
    body = json.dumps(event).encode()
    
    req = urllib.request.Request(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events?sendUpdates=all",
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            event_id = data.get("id")
            print(f"[Calendar] Created event: {event_id}")
            return event_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"[Calendar] Error creating event: {e.code} - {error_body}")
        return None
    except Exception as e:
        print(f"[Calendar] Error creating event: {e}")
        return None


def delete_calendar_event(access_token: str, calendar_id: str, event_id: str) -> bool:
    """Delete a calendar event."""
    req = urllib.request.Request(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}?sendUpdates=all",
        method="DELETE",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"[Calendar] Deleted event: {event_id}")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Event already deleted
            return True
        print(f"[Calendar] Error deleting event: {e.code}")
        return False
    except Exception as e:
        print(f"[Calendar] Error deleting event: {e}")
        return False


def get_calendar_list(access_token: str) -> List[Dict[str, str]]:
    """Get list of user's calendars."""
    req = urllib.request.Request(
        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return [
                {"id": cal["id"], "summary": cal.get("summary", cal["id"])}
                for cal in data.get("items", [])
            ]
    except Exception as e:
        print(f"[Calendar] Error fetching calendars: {e}")
        return []
