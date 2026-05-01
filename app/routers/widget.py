from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import WidgetCustomization, User
from ..security import get_current_user
from ..config import settings

router = APIRouter(prefix="/widget", tags=["widget"])


class WidgetUpdate(BaseModel):
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    font_family: Optional[str] = None
    show_branding: Optional[bool] = None
    custom_header_text: Optional[str] = None
    custom_footer_text: Optional[str] = None


def _get_or_create(db: Session, user: User) -> WidgetCustomization:
    w = db.query(WidgetCustomization).filter(WidgetCustomization.user_id == user.id).first()
    if not w:
        w = WidgetCustomization(user_id=user.id)
        db.add(w)
        db.commit()
        db.refresh(w)
    return w


def _serialize(w: WidgetCustomization, slug: str) -> dict:
    embed = f'<script src="{settings.FRONTEND_URL}/widget.js" data-slug="{slug}"></script>'
    return {
        "primary_color": w.primary_color,
        "secondary_color": w.secondary_color,
        "font_family": w.font_family,
        "show_branding": w.show_branding,
        "custom_header_text": w.custom_header_text,
        "custom_footer_text": w.custom_footer_text,
        "embed_code": embed,
    }


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    w = _get_or_create(db, current_user)
    return _serialize(w, current_user.booking_slug)


@router.put("/settings")
def update_settings(
    body: WidgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    w = _get_or_create(db, current_user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(w, field, value)
    db.commit()
    db.refresh(w)
    return _serialize(w, current_user.booking_slug)


@router.get("/embed-code")
def embed_code(current_user: User = Depends(get_current_user)):
    slug = current_user.booking_slug
    return {
        "embed_code": f'<script src="{settings.FRONTEND_URL}/widget.js" data-slug="{slug}"></script>',
        "iframe_code": f'<iframe src="{settings.FRONTEND_URL}/embed/{slug}" width="100%" height="700" frameborder="0"></iframe>',
        "instructions": "Copy and paste either snippet into your website where you want the booking widget to appear.",
    }
