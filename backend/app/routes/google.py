"""Google Calendar OAuth routes."""

from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import httpx

from ..auth import get_current_user
from ..config import get_settings
from ..database import get_db
from ..models import GoogleAuthResponse, MessageResponse

router = APIRouter(prefix="/api/google", tags=["google"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


@router.get("/auth", response_model=GoogleAuthResponse)
async def google_auth(current_user: dict = Depends(get_current_user)):
    """Get Google OAuth authorization URL."""
    settings = get_settings()
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(current_user["id"])  # Pass user ID in state
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return GoogleAuthResponse(auth_url=auth_url)


@router.get("/callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback."""
    settings = get_settings()
    
    if error:
        # Redirect to settings with error
        return RedirectResponse(
            url=f"{settings.app_url}/#/settings?google=error&message={error}"
        )
    
    if not code or not state:
        return RedirectResponse(
            url=f"{settings.app_url}/#/settings?google=error&message=missing_params"
        )
    
    try:
        user_id = int(state)
    except ValueError:
        return RedirectResponse(
            url=f"{settings.app_url}/#/settings?google=error&message=invalid_state"
        )
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri
            }
        )
        
        if response.status_code != 200:
            return RedirectResponse(
                url=f"{settings.app_url}/#/settings?google=error&message=token_exchange_failed"
            )
        
        tokens = response.json()
    
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    
    if not refresh_token:
        return RedirectResponse(
            url=f"{settings.app_url}/#/settings?google=error&message=no_refresh_token"
        )
    
    # Store tokens
    from datetime import datetime, timedelta
    token_expiry = (datetime.utcnow() + timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M:%S")
    
    with get_db() as conn:
        # Update user with refresh token
        conn.execute(
            "UPDATE users SET google_refresh_token = ? WHERE id = ?",
            (refresh_token, user_id)
        )
        
        # Upsert google_tokens
        conn.execute(
            """
            INSERT INTO google_tokens (user_id, access_token, refresh_token, token_expiry)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                token_expiry = excluded.token_expiry
            """,
            (user_id, access_token, refresh_token, token_expiry)
        )
        conn.commit()
    
    return RedirectResponse(
        url=f"{settings.app_url}/#/settings?google=success"
    )


@router.post("/disconnect", response_model=MessageResponse)
async def disconnect_google(current_user: dict = Depends(get_current_user)):
    """Disconnect Google Calendar integration."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET google_refresh_token = NULL WHERE id = ?",
            (current_user["id"],)
        )
        conn.execute(
            "DELETE FROM google_tokens WHERE user_id = ?",
            (current_user["id"],)
        )
        conn.commit()
    
    return MessageResponse(message="Google Calendar disconnected successfully")
