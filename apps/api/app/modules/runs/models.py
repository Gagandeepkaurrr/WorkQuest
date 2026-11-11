from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, Identity


class Run(Identity, Base):
    __tablename__='runs'
    owner_id: Mapped[UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    scenario_version_id: Mapped[UUID]=mapped_column(ForeignKey('scenario_versions.id'),index=True)
    is_admin_preview: Mapped[bool]=mapped_column(default=False)
    is_demo: Mapped[bool]=mapped_column(default=False)
    preview_definition_private_json: Mapped[dict | None]=mapped_column(JSONB)
    preview_definition_hash: Mapped[str | None]=mapped_column(String(64))
    active_branch_id: Mapped[UUID | None]=mapped_column(ForeignKey('branches.id',use_alter=True,ondelete='SET NULL'))
    last_activity_at: Mapped[datetime | None]
    archived_at: Mapped[datetime | None]


class LearnerProgress(Base):
    __tablename__='learner_scenario_progress'
    owner_id: Mapped[UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    scenario_id: Mapped[UUID]=mapped_column(ForeignKey('scenarios.id'),primary_key=True)
    first_run_id: Mapped[UUID]=mapped_column(ForeignKey('runs.id',ondelete='CASCADE'))


class Branch(Identity, Base):
    __tablename__='branches'
    __table_args__=(CheckConstraint('state_revision >= 0 AND last_event_seq >= 0',name='nonnegative_counters'),)
    run_id: Mapped[UUID]=mapped_column(ForeignKey('runs.id',ondelete='CASCADE'),index=True)
    label: Mapped[str]=mapped_column(String(80))
    parent_branch_id: Mapped[UUID | None]=mapped_column(ForeignKey('branches.id',ondelete='SET NULL'))
    source_checkpoint_id: Mapped[UUID | None]=mapped_column(ForeignKey('checkpoints.id',use_alter=True,ondelete='SET NULL'))
    source_event_seq: Mapped[int]=mapped_column(default=0)
    base_snapshot_private_json: Mapped[dict]=mapped_column(JSONB)
    current_state_private_json: Mapped[dict]=mapped_column(JSONB)
    current_state_hash: Mapped[str]=mapped_column(String(64))
    state_revision: Mapped[int]=mapped_column(default=0)
    last_event_seq: Mapped[int]=mapped_column(default=0)
    status: Mapped[str]=mapped_column(String(20),default='active')
    practice_mode: Mapped[bool]=mapped_column(default=False)
    finalized_at: Mapped[datetime | None]


class BranchEvent(Identity, Base):
    __tablename__='branch_events'
    __table_args__=(UniqueConstraint('branch_id','seq'),)
    branch_id: Mapped[UUID]=mapped_column(ForeignKey('branches.id',ondelete='CASCADE'),index=True)
    seq: Mapped[int]
    type: Mapped[str]=mapped_column(String(100))
    actor_kind: Mapped[str]=mapped_column(String(20),default='learner')
    actor_id: Mapped[UUID | None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    command_id: Mapped[UUID | None]
    state_revision_after: Mapped[int]
    logical_tick: Mapped[int]
    payload_private_json: Mapped[dict]=mapped_column(JSONB,default=dict)
    payload_public_json: Mapped[dict | None]=mapped_column(JSONB)


class CommandRequestRecord(Identity, Base):
    __tablename__='command_requests'
    __table_args__=(UniqueConstraint('user_id','operation_scope','idempotency_key'),)
    user_id: Mapped[UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    operation_scope: Mapped[str]=mapped_column(String(160))
    idempotency_key: Mapped[UUID]
    request_hash: Mapped[str]=mapped_column(String(64))
    response_status: Mapped[int]=mapped_column(default=200)
    response_json: Mapped[dict]=mapped_column(JSONB,default=dict)
    sensitive_response_payload_id: Mapped[UUID | None]=mapped_column(ForeignKey('secret_payloads.id',ondelete='SET NULL'))
    expires_at: Mapped[datetime | None]


class LearnerNote(Base):
    __tablename__='learner_notes'
    branch_id: Mapped[UUID]=mapped_column(ForeignKey('branches.id',ondelete='CASCADE'),primary_key=True)
    body: Mapped[str]=mapped_column(Text,default='')
    revision: Mapped[int]=mapped_column(default=0)
    updated_at: Mapped[datetime | None]
