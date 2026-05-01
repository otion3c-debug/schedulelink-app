from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from ._base import GUID, gen_uuid


class WidgetCustomization(Base):
    __tablename__ = "widget_customizations"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    primary_color = Column(String(7), default="#3B82F6")
    secondary_color = Column(String(7), default="#10B981")
    font_family = Column(String(100), default="Inter")
    show_branding = Column(Boolean, default=True)
    custom_header_text = Column(Text)
    custom_footer_text = Column(Text)
    embed_code = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="widget_customization")
