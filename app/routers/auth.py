from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings
from ..models import User, WidgetCustomization, CalendarConnection
from ..schemas.user import GoogleAuthRequest, TokenPair, UserOut, RefreshRequest
from ..services import google_oauth, microsoft_oauth
from ..security import create_access_token, create_refresh_token, decode_token, encrypt_token
from ..utils import generate_unique_slug
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/url")
def google_login_url():
    return {"authorization_url": google_oauth.build_login_url(state="login")}


@router.post("/google", response_model=TokenPair)
async def google_login(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        token_data = await google_oauth.exchange_code_for_tokens(req.code, req.redirect_uri)
        userinfo = await google_oauth.get_user_info(token_data["access_token"])
    except Exception as e:
        raise HTTPException(400, f"OAuth exchange failed: {e}")

    email = userinfo.get("email")
    if not email:
        raise HTTPException(400, "Email not returned by Google")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        full_name = userinfo.get("name") or email.split("@")[0]
        slug_base = full_name or email.split("@")[0]
        user = User(
            email=email,
            full_name=full_name,
            booking_slug=generate_unique_slug(db, slug_base),
            billing_cycle_start=date.today(),
        )
        db.add(user)
        db.flush()
        db.add(WidgetCustomization(user_id=user.id))
        db.commit()
        db.refresh(user)

    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh")
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(401, "User not found")
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.post("/logout")
def logout():
    # JWT is stateless; client should drop the tokens.
    return {"success": True}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: Session = Depends(get_db),
):
    """Unified Google OAuth callback. State 'login' (or empty) signs in or signs up;
    state 'connect:<user_id>' attaches calendar credentials to that user."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Google callback received, state={state}")
        token_data = await google_oauth.exchange_code_for_tokens(code)
        logger.info("Token exchange successful")
        userinfo = await google_oauth.get_user_info(token_data["access_token"])
        logger.info(f"Got userinfo for {userinfo.get('email')}")
    except Exception as e:
        logger.error(f"OAuth exchange failed: {e}")
        raise HTTPException(400, f"OAuth exchange failed: {e}")

    email = userinfo.get("email")
    if not email:
        raise HTTPException(400, "Email not returned by Google")

    if state.startswith("connect:"):
        user_id = state.split(":", 1)[1]
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            raise HTTPException(400, "User not found")
        if "refresh_token" not in token_data:
            raise HTTPException(400, "No refresh token returned. Revoke prior access in Google account settings and reconnect.")
        existing = (
            db.query(CalendarConnection)
            .filter(
                CalendarConnection.user_id == user.id,
                CalendarConnection.provider == "google",
                CalendarConnection.provider_account_email == email,
            )
            .first()
        )
        is_first = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id).count() == 0
        if existing:
            existing.access_token = encrypt_token(token_data["access_token"])
            existing.refresh_token = encrypt_token(token_data["refresh_token"])
            existing.token_expires_at = google_oauth.expires_at_from_response(token_data)
            existing.is_active = True
            existing.last_sync_at = datetime.utcnow()
        else:
            db.add(CalendarConnection(
                user_id=user.id,
                provider="google",
                provider_account_email=email,
                access_token=encrypt_token(token_data["access_token"]),
                refresh_token=encrypt_token(token_data["refresh_token"]),
                token_expires_at=google_oauth.expires_at_from_response(token_data),
                is_primary=is_first,
                is_active=True,
                last_sync_at=datetime.utcnow(),
            ))
        db.commit()
        return RedirectResponse(f"{settings.FRONTEND_URL}/dashboard/settings?calendar_connected=1")

    # Login / signup flow
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Creating new user for {email}")
            full_name = userinfo.get("name") or email.split("@")[0]
            user = User(
                email=email,
                full_name=full_name,
                booking_slug=generate_unique_slug(db, full_name),
                billing_cycle_start=date.today(),
            )
            db.add(user)
            db.flush()
            db.add(WidgetCustomization(user_id=user.id))
            db.commit()
            db.refresh(user)
            logger.info(f"User created with slug {user.booking_slug}")
        else:
            logger.info(f"Existing user found: {email}")
        user.last_login = datetime.utcnow()
        db.commit()
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        logger.info(f"Redirecting to {settings.FRONTEND_URL}/auth/callback")
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?token={access}&refresh={refresh}")
    except Exception as e:
        logger.error(f"User creation/login failed: {e}")
        db.rollback()
        raise HTTPException(500, f"Login failed: {e}")


@router.get("/microsoft/url")
def microsoft_login_url():
    return {"authorization_url": microsoft_oauth.build_login_url(state="login")}


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: Session = Depends(get_db),
):
    """Unified Microsoft OAuth callback. State 'login' (or empty) signs in or signs up;
    state 'connect:<user_id>' attaches calendar credentials to that user."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Microsoft callback received, state={state}")
        token_data = await microsoft_oauth.exchange_code_for_tokens(code)
        logger.info("Microsoft token exchange successful")
        userinfo = await microsoft_oauth.get_user_info(token_data["access_token"])
        logger.info(f"Got Microsoft userinfo for {userinfo.get('email')}")
    except Exception as e:
        logger.error(f"Microsoft OAuth exchange failed: {e}")
        raise HTTPException(400, f"OAuth exchange failed: {e}")

    email = userinfo.get("email")
    if not email:
        raise HTTPException(400, "Email not returned by Microsoft")

    if state.startswith("connect:"):
        user_id = state.split(":", 1)[1]
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            raise HTTPException(400, "User not found")
        if "refresh_token" not in token_data:
            raise HTTPException(400, "No refresh token returned. Ensure 'offline_access' scope is granted and reconnect.")
        existing = (
            db.query(CalendarConnection)
            .filter(
                CalendarConnection.user_id == user.id,
                CalendarConnection.provider == "microsoft",
                CalendarConnection.provider_account_email == email,
            )
            .first()
        )
        is_first = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id).count() == 0
        if existing:
            existing.access_token = encrypt_token(token_data["access_token"])
            existing.refresh_token = encrypt_token(token_data["refresh_token"])
            existing.token_expires_at = microsoft_oauth.expires_at_from_response(token_data)
            existing.is_active = True
            existing.last_sync_at = datetime.utcnow()
        else:
            db.add(CalendarConnection(
                user_id=user.id,
                provider="microsoft",
                provider_account_email=email,
                access_token=encrypt_token(token_data["access_token"]),
                refresh_token=encrypt_token(token_data["refresh_token"]),
                token_expires_at=microsoft_oauth.expires_at_from_response(token_data),
                is_primary=is_first,
                is_active=True,
                last_sync_at=datetime.utcnow(),
            ))
        db.commit()
        return RedirectResponse(f"{settings.FRONTEND_URL}/dashboard/settings?calendar_connected=1")

    # Login / signup flow
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Creating new user for {email}")
            full_name = userinfo.get("name") or email.split("@")[0]
            user = User(
                email=email,
                full_name=full_name,
                booking_slug=generate_unique_slug(db, full_name),
                billing_cycle_start=date.today(),
            )
            db.add(user)
            db.flush()
            db.add(WidgetCustomization(user_id=user.id))
            db.commit()
            db.refresh(user)
            logger.info(f"User created with slug {user.booking_slug}")
        else:
            logger.info(f"Existing user found: {email}")
        user.last_login = datetime.utcnow()
        db.commit()
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        logger.info(f"Redirecting to {settings.FRONTEND_URL}/auth/callback")
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?token={access}&refresh={refresh}")
    except Exception as e:
        logger.error(f"User creation/login failed: {e}")
        db.rollback()
        raise HTTPException(500, f"Login failed: {e}")
