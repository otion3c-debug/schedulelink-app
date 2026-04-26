"""Authentication routes: register, login, forgot password, reset password."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlite3 import IntegrityError

from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..database import get_db, dict_from_row, seed_working_hours, insert_returning_id
from ..models import (
    UserRegister, UserLogin, Token, UserProfile,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse
)
from ..services.emailer import send_password_reset_email
from ..config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister):
    """Register a new user account."""
    with get_db() as conn:
        # Check if email exists
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? OR username = ?",
            (data.email, data.username)
        ).fetchone()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or username already registered"
            )
        
        # Create user
        password_hash = hash_password(data.password)
        try:
            user_id = insert_returning_id(
                conn,
                "users",
                ["email", "password_hash", "full_name", "username"],
                (data.email, password_hash, data.full_name, data.username.lower())
            )
            
            # Seed default working hours (Mon-Fri, 9-5)
            seed_working_hours(user_id, conn)
            
            conn.commit()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or username already registered"
            )
        
        # Generate token
        access_token = create_access_token(user_id, data.email)
        return Token(access_token=access_token)


@router.post("/login", response_model=Token)
async def login(data: UserLogin):
    """Login with email and password."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (data.email,)
        ).fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user_dict = dict_from_row(user)
        
        if not verify_password(data.password, user_dict["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        access_token = create_access_token(user_dict["id"], user_dict["email"])
        return Token(access_token=access_token)


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserProfile(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        username=current_user["username"],
        timezone=current_user["timezone"],
        meeting_duration=current_user["meeting_duration"],
        buffer_minutes=current_user["buffer_minutes"],
        subscription_status=current_user["subscription_status"],
        google_connected=current_user["google_refresh_token"] is not None,
        created_at=current_user["created_at"]
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest):
    """Send a password reset email to the user."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (data.email,)
        ).fetchone()

        if not user:
            # Don't reveal whether the email exists — still return success
            return MessageResponse(
                message="If an account with that email exists, we sent a reset link."
            )

        user_dict = dict_from_row(user)

        # Generate a cryptographically secure random token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_password(raw_token)

        # Token expires in 1 hour
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        # Store hashed token in DB
        conn.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (user_dict["id"], token_hash, expires_at)
        )
        conn.commit()

        # Build reset link
        reset_link = f"https://schedulelink.tech/app.html#/reset-password?token={raw_token}"

        # Send email
        await send_password_reset_email(
            client_email=user_dict["email"],
            client_name=user_dict["full_name"],
            reset_link=reset_link
        )

        return MessageResponse(
            message="If an account with that email exists, we sent a reset link."
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest):
    """Reset password using a valid reset token."""
    with get_db() as conn:
        # Find all valid (non-used, non-expired) tokens
        rows = conn.execute(
            """
            SELECT id, user_id, token_hash, expires_at
            FROM password_reset_tokens
            WHERE used = 0 AND expires_at > datetime('now')
            """
        ).fetchall()

        found = False
        found_token_id = None
        found_user_id = None
        for row in rows:
            if verify_password(data.token, row["token_hash"]):
                found = True
                found_user_id = row["user_id"]
                found_token_id = row["id"]
                break

        if not found:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token. Please request a new one."
            )

        # Update user's password
        new_hash = hash_password(data.password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, found_user_id)
        )

        # Mark token as used
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE id = ?",
            (found_token_id,)
        )

        conn.commit()

        return MessageResponse(
            message="Your password has been reset successfully. You can now sign in."
        )
