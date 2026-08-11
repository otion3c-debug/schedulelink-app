from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from ..database import Base
from ._base import GUID, gen_uuid


class PageView(Base):
    """A visit/event from the landing page or app (private analytics)."""
    __tablename__ = "page_views"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    event_type = Column(String(50), nullable=False, index=True, default="visit")
    # visit | get_started | pricing | signin_google | signin_microsoft | signup | calendar_connect | booking | checkout_start | purchase
    path = Column(String(255))
    referrer = Column(Text)
    visitor_id = Column(String(64), index=True)  # anonymous hash, no PII
    ip_address = Column(String(45))  # hashed, used only for unique-visitor counting
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # convenience index for funnel queries
    __table_args__ = (
        # (event_type, created_at) covered by separate indexes above
    )
