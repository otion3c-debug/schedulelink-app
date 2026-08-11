import hashlib
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PageView, User, Booking

logger = logging.getLogger("schedulelink.analytics")

router = APIRouter(prefix="/analytics", tags=["analytics"])

VALID_EVENTS = {
    "visit",
    "get_started",
    "pricing",
    "signin_google",
    "signin_microsoft",
    "signup",
    "calendar_connect",
    "booking",
    "checkout_start",
    "purchase",
}


def _hash(value: str) -> str:
    """One-way hash for visitor/IP anonymity (no PII stored)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


class TrackEventRequest(BaseModel):
    event: str = Field(..., description="Event type, e.g. visit, get_started, signup")
    path: str = ""
    referrer: str = ""
    visitor_id: str = ""


@router.post("/track")
def track_event(req: TrackEventRequest, request: Request, db: Session = Depends(get_db)):
    """Record a visit/event from the frontend. Public endpoint — anonymous, no PII."""
    event = req.event if req.event in VALID_EVENTS else "visit"
    client_ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")[:500]

    view = PageView(
        event_type=event,
        path=req.path[:255],
        referrer=req.referrer[:2000],
        visitor_id=_hash(req.visitor_id) if req.visitor_id else "",
        ip_address=_hash(client_ip),
        user_agent=ua,
    )
    db.add(view)
    db.commit()
    return {"ok": True}


@router.get("/stats")
def get_stats(days: int = 30, db: Session = Depends(get_db)):
    """Private funnel stats: traffic → signups → bookings → purchases.

    NOTE: keep this endpoint private — it exposes business numbers.
    """
    since = datetime.utcnow() - timedelta(days=days)

    def count(model_col, *filters):
        q = db.query(func.count(model_col))
        for f in filters:
            q = q.filter(f)
        return q.scalar() or 0

    # Traffic
    total_views = count(PageView.id, PageView.event_type == "visit")
    views_window = count(
        PageView.id, PageView.event_type == "visit", PageView.created_at >= since
    )
    unique_visitors_window = (
        db.query(func.count(func.distinct(PageView.visitor_id)))
        .filter(PageView.event_type == "visit", PageView.created_at >= since)
        .scalar()
        or 0
    )
    unique_visitors_all = (
        db.query(func.count(func.distinct(PageView.visitor_id)))
        .filter(PageView.event_type == "visit")
        .scalar()
        or 0
    )

    # CTAs
    def event_count(event: str, window: bool = True):
        f = [PageView.event_type == event]
        if window:
            f.append(PageView.created_at >= since)
        return count(PageView.id, *f)

    get_started = event_count("get_started")
    pricing_clicks = event_count("pricing")
    google_clicks = event_count("signin_google")
    ms_clicks = event_count("signin_microsoft")

    # Conversions (from real data)
    total_users = count(User.id)
    users_window = count(User.id, User.created_at >= since)
    total_bookings = count(Booking.id)
    bookings_window = count(Booking.id, Booking.created_at >= since)
    paid_users = (
        db.query(func.count(User.id))
        .filter(User.subscription_status == "active", User.subscription_tier != "free")
        .scalar()
        or 0
    )

    # Derived rates
    def pct(part, whole):
        return round((part / whole) * 100, 1) if whole else 0.0

    visit_to_signup = pct(users_window, views_window)
    visit_to_purchase = pct(paid_users, views_window)

    # Daily trend for the last N days (visits only)
    rows = (
        db.query(
            func.date(PageView.created_at).label("day"),
            func.count(PageView.id).label("n"),
        )
        .filter(PageView.event_type == "visit", PageView.created_at >= since)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
        .all()
    )
    trend = [{"date": str(r.day), "visits": r.n} for r in rows]

    return {
        "period_days": days,
        "traffic": {
            "total_views": total_views,
            f"views_last_{days}d": views_window,
            f"unique_visitors_last_{days}d": unique_visitors_window,
            "unique_visitors_all": unique_visitors_all,
        },
        "cta_clicks": {
            "get_started": get_started,
            "pricing": pricing_clicks,
            "signin_google": google_clicks,
            "signin_microsoft": ms_clicks,
        },
        "conversions": {
            "total_users": total_users,
            f"new_users_last_{days}d": users_window,
            "total_bookings": total_bookings,
            f"bookings_last_{days}d": bookings_window,
            "paid_subscriptions": paid_users,
        },
        "rates": {
            f"visit_to_signup_{days}d": visit_to_signup,
            f"visit_to_purchase_{days}d": visit_to_purchase,
        },
        "daily_trend": trend,
        "generated_at": datetime.utcnow().isoformat(),
    }
