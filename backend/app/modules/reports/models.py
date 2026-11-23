from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Identity


class ScorecardRecord(Identity, Base):
    __tablename__ = "scorecards"
    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), unique=True
    )
    terminal_state_revision: Mapped[int]
    scenario_version_id: Mapped[UUID] = mapped_column(ForeignKey("scenario_versions.id"))
    scoring_version: Mapped[str] = mapped_column(String(20))
    criteria_json: Mapped[dict] = mapped_column(JSONB)
    total_score: Mapped[int]
    outcome: Mapped[str] = mapped_column(String(30))
    coaching_status: Mapped[str] = mapped_column(String(20), default="not_requested")
    coaching_text: Mapped[str | None] = mapped_column(Text)
    deterministic_hash: Mapped[str] = mapped_column(String(64))


class ReportShare(Identity, Base):
    __tablename__ = "report_shares"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scorecard_id: Mapped[UUID] = mapped_column(ForeignKey("scorecards.id", ondelete="CASCADE"))
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    sanitized_snapshot_json: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
