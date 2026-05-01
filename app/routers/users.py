from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas.user import UserOut, UserUpdate
from ..security import get_current_user
from ..utils import slugify

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.timezone is not None:
        current_user.timezone = body.timezone
    if body.booking_slug is not None:
        new_slug = slugify(body.booking_slug)
        if not new_slug:
            raise HTTPException(400, "Invalid booking slug")
        existing = db.query(User).filter(User.booking_slug == new_slug, User.id != current_user.id).first()
        if existing:
            raise HTTPException(409, "Slug already taken")
        current_user.booking_slug = new_slug
    db.commit()
    db.refresh(current_user)
    return current_user
