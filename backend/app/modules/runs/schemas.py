from typing import Any
from uuid import UUID

from pydantic import Field

from app.engine.types import VisibleWorldState
from app.modules.auth.schemas import StrictModel


class StartRun(StrictModel):
    scenario_version_id: UUID


class WorldCommandRequest(StrictModel):
    type: str = Field(max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_state_revision: int = Field(ge=0)


class BranchState(StrictModel):
    branch_id: UUID
    run_id: UUID
    label: str
    state_revision: int
    last_event_seq: int
    status: str
    practice_mode: bool
    is_demo: bool
    is_admin_preview: bool
    scenario_title: str
    scenario_slug: str
    projected_state: VisibleWorldState


class CommandResponse(BranchState):
    command_id: UUID
    emitted_public_events: list[dict[str, Any]]
    result: dict[str, Any]


class NoteInput(StrictModel):
    body: str = Field(max_length=20000)
    expected_revision: int = Field(ge=0)


class RevisionInput(StrictModel):
    expected_state_revision: int = Field(ge=0)
