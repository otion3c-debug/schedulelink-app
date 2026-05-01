from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CalendarConnection, User
from ..security import get_current_user
from ..services import google_oauth
import uuid

router = APIRouter(prefix="/calendars", tags=["calendars"])


@router.get("")
def list_calendars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(CalendarConnection).filter(CalendarConnection.user_id == current_user.id).all()
    return {
        "calendars": [
            {
                "id": str(c.id),
                "provider": c.provider,
                "provider_account_email": c.provider_account_email,
                "is_primary": c.is_primary,
                "is_active": c.is_active,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            }
            for c in rows
        ]
    }


@router.post("/connect/google")
def connect_google(current_user: User = Depends(get_current_user)):
    state = f"connect:{current_user.id}"
    return {"authorization_url": google_oauth.build_calendar_connect_url(state=state)}


@router.post("/{calendar_id}/set-primary")
def set_primary(
    calendar_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cal = db.query(CalendarConnection).filter(
        CalendarConnection.id == uuid.UUID(calendar_id),
        CalendarConnection.user_id == current_user.id,
    ).first()
    if not cal:
        raise HTTPException(404, "Calendar not found")
    db.query(CalendarConnection).filter(
        CalendarConnection.user_id == current_user.id
    ).update({"is_primary": False})
    cal.is_primary = True
    db.commit()
    return {"success": True, "message": "Primary calendar updated"}


@router.delete("/{calendar_id}")
def disconnect(
    calendar_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cal = db.query(CalendarConnection).filter(
        CalendarConnection.id == uuid.UUID(calendar_id),
        CalendarConnection.user_id == current_user.id,
    ).first()
    if not cal:
        raise HTTPException(404, "Calendar not found")
    db.delete(cal)
    db.commit()
    return {"success": True, "message": "Calendar disconnected"}
