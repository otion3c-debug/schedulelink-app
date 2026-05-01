import re
from sqlalchemy.orm import Session
from .models import User


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "user"


def generate_unique_slug(db: Session, base: str) -> str:
    slug = slugify(base)
    if not db.query(User).filter(User.booking_slug == slug).first():
        return slug
    i = 2
    while True:
        candidate = f"{slug}-{i}"
        if not db.query(User).filter(User.booking_slug == candidate).first():
            return candidate
        i += 1
