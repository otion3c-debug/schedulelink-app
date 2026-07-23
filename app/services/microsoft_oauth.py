"""Microsoft (Azure AD / Entra ID) OAuth integration."""
from datetime import datetime, timedelta
from typing import Optional
import httpx
from urllib.parse import urlencode
from ..config import settings


def _authority() -> str:
    tenant = settings.MICROSOFT_TENANT_ID or "common"
    return f"https://login.microsoftonline.com/{tenant}"


def _auth_url() -> str:
    return f"{_authority()}/oauth2/v2.0/authorize"


def _token_url() -> str:
    return f"{_authority()}/oauth2/v2.0/token"


MS_GRAPH_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

LOGIN_SCOPES = ["openid", "email", "profile", "User.Read"]
CALENDAR_SCOPES = ["openid", "email", "profile", "User.Read", "Calendars.ReadWrite", "offline_access"]


def build_login_url(state: Optional[str] = None) -> str:
    """OAuth URL for initial login (identity only)."""
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(LOGIN_SCOPES),
        "response_mode": "query",
        "prompt": "select_account",
    }
    if state:
        params["state"] = state
    return f"{_auth_url()}?{urlencode(params)}"


def build_calendar_connect_url(state: str) -> str:
    """OAuth URL for connecting a calendar (full calendar scopes + refresh token)."""
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(CALENDAR_SCOPES),
        "response_mode": "query",
        "prompt": "consent",
        "state": state,
    }
    return f"{_auth_url()}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str, redirect_uri: Optional[str] = None) -> dict:
    """Exchange authorization code for access + refresh tokens.

    When a personal Microsoft account authenticates through the ``common``
    endpoint, Azure issues a code that can only be redeemed against the
    ``consumers`` tenant.  This function tries the configured tenant first;
    if Azure replies with ``AADSTS7000012`` (wrong tenant), it falls back
    to ``consumers`` automatically.
    """
    async def _try_exchange(tenant: str) -> dict:
        url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                data={
                    "code": code,
                    "client_id": settings.MICROSOFT_CLIENT_ID,
                    "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                    "redirect_uri": redirect_uri or settings.MICROSOFT_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.is_success:
                return resp.json()
            body = resp.json() if resp.text else {}
            # AADSTS7000012 = grant obtained for a different tenant -> fall back
            if resp.status_code == 400 and any(
                "AADSTS7000012" in str(v) for v in body.values()
            ):
                raise _WrongTenant("Grant obtained for a different tenant", tenant)
            resp.raise_for_status()
            return resp.json()  # unreachable, keep mypy happy

    class _WrongTenant(Exception):
        def __init__(self, msg: str, tried_tenant: str):
            self.tried_tenant = tried_tenant
            super().__init__(msg)

    configured_tenant = settings.MICROSOFT_TENANT_ID or "common"
    try:
        return await _try_exchange(configured_tenant)
    except _WrongTenant as exc:
        # The code was issued for a different tenant.  Personal Microsoft
        # accounts almost always need ``consumers``.
        fallback = "consumers" if exc.tried_tenant == "common" else "common"
        return await _try_exchange(fallback)


async def get_user_info(access_token: str) -> dict:
    """Fetch the signed-in user's profile from Microsoft Graph."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            MS_GRAPH_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
    # Normalize to a Google-like shape so callers can rely on `email` / `name`.
    email = data.get("mail") or data.get("userPrincipalName")
    return {
        "email": email,
        "name": data.get("displayName"),
        "id": data.get("id"),
        "raw": data,
    }


async def refresh_access_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _token_url(),
            data={
                "refresh_token": refresh_token,
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "scope": " ".join(CALENDAR_SCOPES),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


def expires_at_from_response(token_response: dict) -> datetime:
    expires_in = int(token_response.get("expires_in", 3600))
    return datetime.utcnow() + timedelta(seconds=expires_in)
