"""Public transport projections. Private models are never response DTOs."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.modules.auth.schemas import StrictModel

BranchStatus = Literal["active", "paused", "finalized"]
JobStatus = Literal[
    "queued", "running", "failed", "stale", "cancelled", "completed", "quota_limited"
]
ErrorCode = Literal[
    "UNAUTHENTICATED",
    "FORBIDDEN",
    "NOT_FOUND",
    "VALIDATION_ERROR",
    "RATE_LIMITED",
    "PRECONDITION_FAILED",
    "STALE_REVISION",
    "IDEMPOTENCY_CONFLICT",
    "RESULT_EXPIRED",
    "AI_BUSY",
    "AI_QUOTA_EXCEEDED",
    "AI_UNAVAILABLE",
    "DEPENDENCY_UNAVAILABLE",
    "LOGICAL_CAP_EXCEEDED",
    "BRANCH_FINALIZED",
    "CHECKPOINT_NOT_SETTLED",
    "INVALID_ACTION",
    "SCENARIO_VERSION_UNSUPPORTED",
]


class ErrorDetail(StrictModel):
    code: ErrorCode
    message: str
    details: Any = None


class ErrorEnvelope(StrictModel):
    error: ErrorDetail
    request_id: str


class RunView(StrictModel):
    id: UUID
    active_branch_id: UUID
    scenario_title: str
    scenario_slug: str
    scenario_version_id: UUID
    is_demo: bool
    is_admin_preview: bool
    created_at: datetime
    archived: bool
    status: BranchStatus | None = None
    simulation_time: int | None = None
    practice_mode: bool | None = None


class RunPage(StrictModel):
    items: list[RunView]
    next_offset: int | None


class EventView(StrictModel):
    id: UUID
    seq: int
    type: str
    logical_tick: int
    state_revision: int
    payload: dict[str, Any]
    created_at: datetime


class EventPage(StrictModel):
    items: list[EventView]
    inherited_prefix: list[EventView]
    cursor: str
    last_event_seq: int


class JobView(StrictModel):
    id: UUID
    job_id: UUID
    kind: Literal["dialogue", "debrief"]
    status: JobStatus
    attempt_count: int
    failure_code: str | None
    captured_state_revision: int
    created_at: datetime
    retry_available: bool


class ConversationView(StrictModel):
    items: list[EventView]
    jobs: list[JobView]


class PublicCriterion(StrictModel):
    title: str
    awarded_points: int
    maximum_points: int


class PublicReport(StrictModel):
    title: str
    version: int
    completed_at: datetime
    outcome: Literal["successful", "contained", "unresolved"]
    total_score: int = Field(ge=0, le=100)
    criteria: list[PublicCriterion]
    practice_mode: bool
    hints_used: int
    alias: str
    label: str


class ShareResult(StrictModel):
    share_id: UUID
    url: str
    expires_at: datetime
    snapshot: PublicReport
