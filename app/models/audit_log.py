from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from ..database import Base
from ._base import GUID, gen_uuid


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(GUID(), primary_key=True, default=gen_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(GUID())
    audit_metadata = Column("metadata", JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
