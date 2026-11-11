from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, Identity


class ScenarioRecord(Identity, Base):
    __tablename__='scenarios'
    slug: Mapped[str]=mapped_column(String(100),unique=True)
    public_metadata: Mapped[dict]=mapped_column(JSONB)
    active_published_version_id: Mapped[UUID | None]=mapped_column(ForeignKey('scenario_versions.id',use_alter=True,ondelete='SET NULL'))
    archived_at: Mapped[datetime | None]
    created_by: Mapped[UUID | None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))


class ScenarioVersion(Identity, Base):
    __tablename__='scenario_versions'
    __table_args__=(UniqueConstraint('scenario_id','version_number'),)
    scenario_id: Mapped[UUID]=mapped_column(ForeignKey('scenarios.id',ondelete='CASCADE'),index=True)
    version_number: Mapped[int]
    status: Mapped[str]=mapped_column(String(20),default='draft')
    schema_version: Mapped[str]=mapped_column(String(20),default='1')
    mechanics_id: Mapped[str]=mapped_column(String(50))
    engine_version: Mapped[str]=mapped_column(String(20),default='1')
    scoring_version: Mapped[str]=mapped_column(String(20),default='1')
    definition_private_json: Mapped[dict]=mapped_column(JSONB)
    content_hash: Mapped[str]=mapped_column(String(64))
    draft_revision: Mapped[int]=mapped_column(default=0)
    validation_report: Mapped[dict | None]=mapped_column(JSONB)
    validated_hash: Mapped[str | None]=mapped_column(String(64))
    published_at: Mapped[datetime | None]
    created_by: Mapped[UUID | None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
