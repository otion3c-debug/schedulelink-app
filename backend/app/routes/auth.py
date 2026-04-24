"""Authentication routes: register, login."""

from fastapi import APIRouter, HTTPException, status
from sqlite3 import IntegrityError

from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..database import get_db, dict_from_row, seed_working_hours
from ..models import UserRegister, UserLogin, Token, UserProfile
from fastapi import Depends

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
            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name, username)
                VALUES (?, ?, ?, ?)
                """,
                (data.email, password_hash, data.full_name, data.username.lower())
            )
            user_id = cursor.lastrowid
            
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
