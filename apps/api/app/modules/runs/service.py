from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.core.errors import AppError, unavailable
from app.core.security import now
from app.db.sessions import Session
from app.engine.projections import project_visible_state
from app.engine.scoring import evaluate_score
from app.engine.transitions import apply_command, initial_state
from app.engine.types import Command, Scenario
from app.modules.checkpoints.service import capture_checkpoint
from app.modules.reports.models import ScorecardRecord
from app.modules.runs.models import Branch, LearnerNote, LearnerProgress, Run
from app.modules.runs.repository import (
    append_event,
    assert_revision,
    event_view,
    idempotent_record,
    lock_owner,
    owned_branch,
    parse_state,
)
from app.modules.runs.schemas import BranchState, CommandResponse, WorldCommandRequest
from app.modules.scenarios.models import ScenarioRecord, ScenarioVersion


def state_view(branch: Branch, run: Run, scenario: Scenario) -> BranchState:
    return BranchState(
        branch_id=branch.id,
        run_id=run.id,
        label=branch.label,
        state_revision=branch.state_revision,
        last_event_seq=branch.last_event_seq,
        status=branch.status,
        practice_mode=branch.practice_mode,
        is_demo=run.is_demo,
        is_admin_preview=run.is_admin_preview,
        scenario_title=scenario.metadata.title,
        scenario_slug=scenario.slug,
        projected_state=project_visible_state(parse_state(branch), scenario),
    )


def run_view(run: Run, scenario: Scenario) -> dict:
    return {
        "id": str(run.id),
        "active_branch_id": str(run.active_branch_id),
        "scenario_title": scenario.metadata.title,
        "scenario_slug": scenario.slug,
        "scenario_version_id": str(run.scenario_version_id),
        "is_demo": run.is_demo,
        "is_admin_preview": run.is_admin_preview,
        "created_at": run.created_at.isoformat(),
        "archived": bool(run.archived_at),
    }


async def create_run(owner_id: UUID, version_id: UUID, key: UUID, preview: bool = False):
    async with Session.begin() as db:
        user = await lock_owner(db, owner_id)
        record, repeated = await idempotent_record(
            db,
            owner_id,
            "preview" if preview else "runs",
            key,
            {"scenario_version_id": str(version_id)},
        )
        if repeated:
            return record.response_json
        version = await db.get(ScenarioVersion, version_id)
        scenario_record = await db.get(ScenarioRecord, version.scenario_id) if version else None
        if not version or not scenario_record:
            raise unavailable()
        if preview:
            if user.role != "admin":
                raise unavailable()
            if (
                version.validated_hash != version.content_hash
                or not version.validation_report
                or not version.validation_report.get("passed")
            ):
                raise AppError(
                    "PRECONDITION_FAILED", "Validate this draft before creating a preview.", 409
                )
        elif (
            version.status != "published"
            or scenario_record.archived_at
            or scenario_record.active_published_version_id != version.id
        ):
            raise unavailable()
        scenario = Scenario.model_validate(version.definition_private_json)
        if user.demo_expires_at and scenario.slug != "checkout-outage":
            raise unavailable()
        count = await db.scalar(
            select(func.count())
            .select_from(Run)
            .where(Run.owner_id == owner_id, Run.archived_at.is_(None))
        )
        if (count or 0) >= (2 if user.demo_expires_at else 20):
            raise AppError("RATE_LIMITED", "Archive an older run before starting another.", 429)
        run = Run(
            owner_id=owner_id,
            scenario_version_id=version.id,
            is_admin_preview=preview,
            is_demo=bool(user.demo_expires_at),
            preview_definition_private_json=scenario.model_dump() if preview else None,
            preview_definition_hash=version.content_hash if preview else None,
        )
        db.add(run)
        await db.flush()
        first = None
        if not preview and not user.demo_expires_at:
            first = await db.get(LearnerProgress, (owner_id, scenario_record.id))
            if not first:
                db.add(
                    LearnerProgress(
                        owner_id=owner_id, scenario_id=scenario_record.id, first_run_id=run.id
                    )
                )
        state = initial_state(scenario)
        branch = Branch(
            run_id=run.id,
            label="First approach",
            practice_mode=bool(first),
            base_snapshot_private_json={
                "state": state.model_dump(),
                "notes": {"body": "", "revision": 0},
                "prefix": [],
            },
            current_state_private_json=state.model_dump(),
            current_state_hash=state.canonical_hash(),
            state_revision=0,
            last_event_seq=0,
        )
        db.add(branch)
        await db.flush()
        run.active_branch_id = branch.id
        db.add(LearnerNote(branch_id=branch.id, body="", revision=0))
        await append_event(
            db,
            branch,
            "branch.created",
            {"label": branch.label, "practice_mode": branch.practice_mode},
        )
        for teammate in scenario.teammates:
            await append_event(
                db,
                branch,
                "message.assistant",
                {
                    "teammate_id": teammate.id,
                    "reply_text": teammate.welcome,
                    "citations": [],
                    "provider": "authored",
                },
            )
        await capture_checkpoint(db, branch, "Mission start")
        record.response_status = 201
        record.response_json = run_view(run, scenario)
        return record.response_json


async def has_pending_dialogue(db, branch_id):
    from app.jobs.models import AIJob

    return bool(
        await db.scalar(
            select(AIJob.id).where(
                AIJob.branch_id == branch_id,
                AIJob.kind == "dialogue",
                AIJob.status.in_(["queued", "running"]),
            )
        )
    )


async def execute_world_command(
    owner_id: UUID, branch_id: UUID, idempotency_key: UUID, request: WorldCommandRequest
) -> dict:
    async with Session.begin() as db:
        await lock_owner(db, owner_id)
        branch, run, scenario = await owned_branch(db, owner_id, branch_id, lock=True)
        record, repeated = await idempotent_record(
            db, owner_id, f"commands:{branch_id}", idempotency_key, request.model_dump(mode="json")
        )
        if repeated:
            return record.response_json
        assert_revision(branch, request.expected_state_revision)
        if branch.status != "active":
            raise AppError(
                "BRANCH_FINALIZED" if branch.status == "finalized" else "PRECONDITION_FAILED",
                "Resume this branch or choose a new approach.",
                409,
            )
        origin = uuid4()
        transition = apply_command(
            parse_state(branch),
            Command(type=request.type, payload=request.payload, origin_id=str(origin)),
            scenario,
        )
        pending = await has_pending_dialogue(db, branch_id)
        action = next((a for a in scenario.action_catalog if a.id == request.type), None)
        if action and action.mutation and not pending:
            await capture_checkpoint(db, branch, f"Before {action.label}")
        branch.current_state_private_json = transition.next_state.model_dump()
        branch.current_state_hash = transition.next_state.canonical_hash()
        branch.state_revision += 1
        run.last_activity_at = now()
        run.active_branch_id = branch.id
        events = []
        for index, event in enumerate(transition.events):
            saved = await append_event(
                db,
                branch,
                event["type"],
                event,
                owner_id,
                event_id=origin if index == 0 else None,
                command_id=record.id,
            )
            events.append(event_view(saved))
        if transition.next_state.finalized:
            branch.status = "finalized"
            branch.finalized_at = now()
            score = evaluate_score(transition.next_state, scenario)
            db.add(
                ScorecardRecord(
                    branch_id=branch.id,
                    terminal_state_revision=branch.state_revision,
                    scenario_version_id=run.scenario_version_id,
                    scoring_version=scenario.scoring_version,
                    criteria_json=score.model_dump(),
                    total_score=score.total_score,
                    outcome=score.outcome,
                    deterministic_hash=score.deterministic_hash,
                )
            )
        response = CommandResponse(
            **state_view(branch, run, scenario).model_dump(),
            command_id=record.id,
            emitted_public_events=events,
            result={
                **transition.result,
                "automatic_checkpoint_skipped": bool(action and action.mutation and pending),
            },
        )
        record.response_json = response.model_dump(mode="json")
        return record.response_json
