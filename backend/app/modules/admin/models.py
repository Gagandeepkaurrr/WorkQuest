from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Identity


class AdminAudit(Identity, Base):
    __tablename__ = "admin_audit_events"
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    operation: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[UUID | None]
    content_hash: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(40))
    safe_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
