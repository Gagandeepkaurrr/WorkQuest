from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey,Index,String,UniqueConstraint,text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base,Identity


class AIJob(Identity,Base):
    __tablename__='ai_jobs'
    __table_args__=(Index('uq_active_dialogue','branch_id',unique=True,postgresql_where=text("kind='dialogue' AND status IN ('queued','running')")),)
    branch_id: Mapped[UUID]=mapped_column(ForeignKey('branches.id',ondelete='CASCADE'),index=True)
    kind: Mapped[str]=mapped_column(String(20),default='dialogue')
    request_event_id: Mapped[UUID | None]=mapped_column(ForeignKey('branch_events.id',ondelete='CASCADE'))
    captured_state_revision: Mapped[int]
    captured_event_seq: Mapped[int]
    eligible_context_private_json: Mapped[dict | None]=mapped_column(JSONB)
    input_hash: Mapped[str]=mapped_column(String(64))
    status: Mapped[str]=mapped_column(String(20),default='queued',index=True)
    attempt_count: Mapped[int]=mapped_column(default=0)
    lease_token: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None]
    next_attempt_at: Mapped[datetime | None]
    result_event_id: Mapped[UUID | None]=mapped_column(ForeignKey('branch_events.id',ondelete='SET NULL'))
    failure_code: Mapped[str | None]=mapped_column(String(50))
    last_dispatched_at: Mapped[datetime | None]
    scorecard_id: Mapped[UUID | None]=mapped_column(ForeignKey('scorecards.id',ondelete='CASCADE'))
    captured_scorecard_hash: Mapped[str | None]=mapped_column(String(64))
    updated_at: Mapped[datetime | None]


class CallAttempt(Identity,Base):
    __tablename__='ai_call_attempts'
    __table_args__=(UniqueConstraint('job_id','attempt_number'),)
    job_id: Mapped[UUID]=mapped_column(ForeignKey('ai_jobs.id',ondelete='CASCADE'),index=True)
    attempt_number: Mapped[int]
    provider: Mapped[str]=mapped_column(String(30))
    model: Mapped[str]=mapped_column(String(100))
    prompt_version: Mapped[str]=mapped_column(String(40))
    finished_at: Mapped[datetime | None]
    outcome: Mapped[str]=mapped_column(String(30),default='unknown')
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    estimated_cost: Mapped[str | None]=mapped_column(String(40))
    cost_currency: Mapped[str | None]=mapped_column(String(10))
    cost_certainty: Mapped[str]=mapped_column(String(40),default='unknown')
    pricing_version: Mapped[str | None]=mapped_column(String(40))


class UsageCounter(Base):
    __tablename__='usage_counters'
    scope: Mapped[str]=mapped_column(String(120),primary_key=True)
    period: Mapped[str]=mapped_column(String(10),primary_key=True)
    accepted_requests: Mapped[int]=mapped_column(default=0)
    reserved_requests: Mapped[int]=mapped_column(default=0)
    reserved_tokens: Mapped[int]=mapped_column(default=0)
    measured_tokens: Mapped[int]=mapped_column(default=0)
    updated_at: Mapped[datetime | None]
