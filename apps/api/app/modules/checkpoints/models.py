from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Identity


class Checkpoint(Identity, Base):
    __tablename__ = "checkpoints"
    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(100))
    source_state_revision: Mapped[int]
    source_event_seq: Mapped[int]
    state_hash: Mapped[str] = mapped_column(String(64))
    snapshot_private_json: Mapped[dict] = mapped_column(JSONB)
    display_prefix_json: Mapped[list] = mapped_column(JSONB, default=list)
