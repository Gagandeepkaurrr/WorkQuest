"""Pure engine contracts. No database, clock, network or provider dependencies."""

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Metadata(Strict):
    title: str = Field(max_length=120)
    description: str = Field(max_length=500)
    company: str = Field(max_length=80)
    role: str = Field(max_length=80)
    difficulty: Literal["Beginner", "Intermediate"]
    duration: str = Field(max_length=40)
    tags: list[str] = Field(max_length=10)
    briefing: str = Field(max_length=6000)
    objectives: list[str] = Field(min_length=4, max_length=10)


class Artifact(Strict):
    id: str
    title: str
    type: Literal["text", "markdown", "log", "table", "diagram"]
    body: str = Field(max_length=30000)
    requires: list[str] = Field(default_factory=list, max_length=10)
    first_open_cost: Literal[1] = 1
    teammate: Literal["maya", "leo"]


class Fact(Strict):
    id: str
    text: str = Field(max_length=2000)
    artifact_id: str | None = None
    teammates: list[Literal["maya", "leo"]]


class Teammate(Strict):
    id: Literal["maya", "leo"]
    name: str
    role: str
    persona: str
    fallback: str
    welcome: str


class Parameter(Strict):
    name: str
    label: str
    type: Literal["boolean", "enum"]
    choices: list[str] = Field(default_factory=list, max_length=10)


class Action(Strict):
    id: str
    label: str
    description: str
    cost: int = Field(ge=0, le=3)
    requires: list[str] = Field(default_factory=list, max_length=10)
    parameters: list[Parameter] = Field(default_factory=list, max_length=5)
    mutation: bool = True
    target: str = "Simulated service"


class Choice(Strict):
    id: str
    label: str


class Hint(Strict):
    id: str
    text: str
    requires: list[str] = Field(default_factory=list)


class Rubric(Strict):
    cause_id: str
    diagnosis_artifacts: list[str] = Field(min_length=2, max_length=2)
    explanation: str
    weights: dict[str, int] = Field(
        default_factory=lambda: {
            "diagnosis": 20,
            "outcome": 40,
            "verification": 20,
            "communication": 10,
            "judgment": 10,
        }
    )


class Scenario(Strict):
    schema_version: Literal["1"] = "1"
    scenario_id: str
    slug: str
    content_version: int = Field(ge=1)
    mechanics_id: Literal["checkout_v1", "inventory_v1", "analytics_v1"]
    engine_version: Literal["1"] = "1"
    scoring_version: Literal["1"] = "1"
    metadata: Metadata
    initial_state: dict[str, Any]
    teammates: list[Teammate] = Field(min_length=2, max_length=2)
    facts: list[Fact] = Field(max_length=100)
    artifacts: list[Artifact] = Field(min_length=3, max_length=30)
    action_catalog: list[Action] = Field(max_length=30)
    diagnosis_choices: list[Choice] = Field(min_length=3, max_length=6)
    rubric: Rubric
    hints: list[Hint] = Field(min_length=2, max_length=5)
    golden_commands: list[dict[str, Any]] = Field(max_length=50)
    golden_expected: dict[str, Any]
    negative_paths: list[list[dict[str, Any]]] = Field(max_length=20)


class Command(Strict):
    type: str = Field(max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    origin_id: str = Field(max_length=100)


class WorldState(Strict):
    simulation_time: int = Field(default=0, ge=0, le=20)
    domain: dict[str, Any]
    opened: list[str] = Field(default_factory=list)
    diagnosis: str | None = None
    updates: list[dict[str, Any]] = Field(default_factory=list)
    recap: dict[str, Any] | None = None
    hints: list[str] = Field(default_factory=list)
    verifications: dict[str, dict[str, Any]] = Field(default_factory=dict)
    ledger: list[dict[str, Any]] = Field(default_factory=list)
    metric_history: list[dict[str, Any]] = Field(default_factory=list)
    finalized: bool = False

    def canonical_hash(self) -> str:
        return canonical_hash(self.model_dump())


class TransitionResult(Strict):
    next_state: WorldState
    events: list[dict[str, Any]]
    ticks_applied: int
    result: dict[str, Any]


class ArtifactMetadata(Strict):
    id: str
    title: str
    type: str
    opened: bool
    first_open_cost: int
    teammate: str


class VisibleAction(Action):
    available: bool
    missing_evidence: list[str]


class TaskView(Strict):
    id: str
    label: str
    completed: bool


class VerificationView(Strict):
    passed: bool
    current: bool
    detail: str
    logical_tick: int
    origin_id: str


class CommunicationView(Strict):
    impact: int
    status: str
    next_actions: list[str]
    outcome: str


class TeammateView(Strict):
    id: str
    name: str
    role: str
    welcome: str


class VisibleWorldState(Strict):
    simulation_time: int
    logical_cap: Literal[20] = 20
    finalized: bool
    metrics: dict[str, Any]
    metric_history: list[dict[str, Any]]
    artifacts: list[ArtifactMetadata]
    actions: list[VisibleAction]
    tasks: list[TaskView]
    diagnosis_choices: list[Choice]
    diagnosis: str | None
    verifications: dict[str, VerificationView]
    communication: CommunicationView
    hints: list[dict[str, str]]
    teammates: list[TeammateView]
    rubric: dict[str, int]


class Criterion(Strict):
    criterion_id: str
    title: str
    maximum_points: int
    awarded_points: int
    explanation: str
    supporting_origin_ids: list[str]


class Scorecard(Strict):
    total_score: int = Field(ge=0, le=100)
    outcome: Literal["successful", "contained", "unresolved"]
    criteria: list[Criterion]
    simulation_time: int
    hints_used: list[str]
    metrics: dict[str, Any]
    action_sequence: list[dict[str, Any]]
    explanation: str
    missed_checks: list[str]
    deterministic_hash: str = ""


class ReplayResult(Strict):
    state: WorldState
    state_hash: str
    matched: bool = True
