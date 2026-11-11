from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import Auth, current_auth
from app.core.errors import AppError, unavailable
from app.db.sessions import Session, get_db
from app.engine.projections import project_visible_state
from app.engine.replay import replay_branch
from app.engine.types import WorldState
from app.modules.auth.schemas import StrictModel
from app.modules.checkpoints.models import Checkpoint
from app.modules.checkpoints.service import capture_checkpoint
from app.modules.reports.models import ScorecardRecord
from app.modules.runs.models import Branch, LearnerNote
from app.modules.runs.repository import (
    append_event,
    assert_revision,
    idempotent_record,
    lock_owner,
    owned_branch,
    owned_run,
    parse_state,
)
from app.modules.runs.service import has_pending_dialogue, state_view

router = APIRouter(tags=["branches"])


class CheckpointInput(StrictModel):
    expected_state_revision: int = Field(ge=0)
    label: str = Field(min_length=1, max_length=80)


class ForkInput(StrictModel):
    label: str = Field(min_length=1, max_length=80)


class SelectBranchInput(StrictModel):
    branch_id: UUID


def checkpoint_view(cp: Checkpoint):
    return {
        "id": str(cp.id),
        "label": cp.label,
        "source_state_revision": cp.source_state_revision,
        "source_event_seq": cp.source_event_seq,
        "simulation_time": cp.snapshot_private_json["state"]["simulation_time"],
        "created_at": cp.created_at.isoformat(),
    }


async def create_checkpoint(
    owner_id: UUID, branch_id: UUID, expected_state_revision: int, label: str, key: UUID
):
    async with Session.begin() as db:
        await lock_owner(db, owner_id)
        branch, _, _ = await owned_branch(db, owner_id, branch_id, lock=True)
        record, repeated = await idempotent_record(
            db,
            owner_id,
            f"checkpoint:{branch_id}",
            key,
            {"expected_state_revision": expected_state_revision, "label": label},
        )
        if repeated:
            return record.response_json
        assert_revision(branch, expected_state_revision)
        if branch.status == "finalized":
            raise AppError(
                "BRANCH_FINALIZED",
                "Choose an existing checkpoint from this completed attempt.",
                409,
            )
        if await has_pending_dialogue(db, branch_id):
            raise AppError(
                "CHECKPOINT_NOT_SETTLED",
                "Wait for or cancel the pending teammate reply before saving a checkpoint.",
                409,
            )
        cp = await capture_checkpoint(db, branch, label)
        record.response_status = 201
        record.response_json = checkpoint_view(cp)
        return record.response_json


async def fork_checkpoint(owner_id: UUID, checkpoint_id: UUID, label: str, key: UUID):
    async with Session.begin() as db:
        user = await lock_owner(db, owner_id)
        cp = await db.get(Checkpoint, checkpoint_id)
        if not cp:
            raise unavailable()
        parent, run, scenario = await owned_branch(db, owner_id, cp.branch_id, lock=True)
        record, repeated = await idempotent_record(
            db, owner_id, f"fork:{checkpoint_id}", key, {"label": label}
        )
        if repeated:
            return record.response_json
        count = await db.scalar(
            select(func.count()).select_from(Branch).where(Branch.run_id == run.id)
        )
        if (count or 0) >= (3 if user.demo_expires_at else 10):
            raise AppError("RATE_LIMITED", "This run has reached its branch limit.", 429)
        state = WorldState.model_validate(cp.snapshot_private_json["state"])
        if state.finalized:
            raise AppError("PRECONDITION_FAILED", "This checkpoint is already terminal.", 409)
        child = Branch(
            run_id=run.id,
            label=label,
            parent_branch_id=parent.id,
            source_checkpoint_id=cp.id,
            source_event_seq=cp.source_event_seq,
            base_snapshot_private_json=cp.snapshot_private_json,
            current_state_private_json=state.model_dump(),
            current_state_hash=state.canonical_hash(),
            state_revision=0,
            last_event_seq=0,
            status="active",
            practice_mode=True,
        )
        db.add(child)
        await db.flush()
        note = cp.snapshot_private_json["notes"]
        db.add(LearnerNote(branch_id=child.id, body=note["body"], revision=note["revision"]))
        await append_event(
            db,
            child,
            "branch.created",
            {"label": label, "source_checkpoint_id": str(cp.id), "practice_mode": True},
        )
        await capture_checkpoint(db, child, "Branch starting point")
        run.active_branch_id = child.id
        record.response_status = 201
        record.response_json = state_view(child, run, scenario).model_dump(mode="json")
        return record.response_json


@router.get("/branches/{branch_id}/checkpoints")
async def checkpoints(
    branch_id: UUID, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    await owned_branch(db, auth.id, branch_id)
    rows = (
        await db.scalars(
            select(Checkpoint)
            .where(Checkpoint.branch_id == branch_id)
            .order_by(Checkpoint.created_at.desc())
            .limit(100)
        )
    ).all()
    return {"items": [checkpoint_view(c) for c in rows]}


@router.post("/branches/{branch_id}/checkpoints", status_code=201)
async def checkpoint(
    branch_id: UUID,
    body: CheckpointInput,
    auth: Auth = Depends(current_auth),
    idempotency_key: UUID = Header(),
):
    return await create_checkpoint(
        auth.id, branch_id, body.expected_state_revision, body.label, idempotency_key
    )


@router.post("/checkpoints/{checkpoint_id}/fork", status_code=201)
async def fork(
    checkpoint_id: UUID,
    body: ForkInput,
    auth: Auth = Depends(current_auth),
    idempotency_key: UUID = Header(),
):
    return await fork_checkpoint(auth.id, checkpoint_id, body.label, idempotency_key)


@router.get("/runs/{run_id}/branches")
async def branches(
    run_id: UUID, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    await owned_run(db, auth.id, run_id)
    rows = (
        await db.scalars(select(Branch).where(Branch.run_id == run_id).order_by(Branch.created_at))
    ).all()
    return {
        "items": [
            {
                "id": str(b.id),
                "label": b.label,
                "status": b.status,
                "practice_mode": b.practice_mode,
                "parent_branch_id": str(b.parent_branch_id) if b.parent_branch_id else None,
                "source_checkpoint_id": str(b.source_checkpoint_id)
                if b.source_checkpoint_id
                else None,
                "simulation_time": b.current_state_private_json["simulation_time"],
            }
            for b in rows
        ]
    }


@router.post("/runs/{run_id}/select-branch")
async def select_branch(
    run_id: UUID,
    body: SelectBranchInput,
    auth: Auth = Depends(current_auth),
    idempotency_key: UUID = Header(),
):
    async with Session.begin() as db:
        await lock_owner(db, auth.id)
        branch, run, _ = await owned_branch(db, auth.id, body.branch_id)
        if run.id != run_id:
            raise unavailable()
        record, repeated = await idempotent_record(
            db, auth.id, f"select:{run_id}", idempotency_key, body.model_dump(mode="json")
        )
        if repeated:
            return record.response_json
        run.active_branch_id = branch.id
        record.response_json = {"active_branch_id": str(branch.id)}
        return record.response_json


@router.get("/branches/{branch_id}/replay")
async def replay(
    branch_id: UUID, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    branch, _, scenario = await owned_branch(db, auth.id, branch_id)
    result = replay_branch(
        WorldState.model_validate(branch.base_snapshot_private_json["state"]),
        parse_state(branch).ledger,
        scenario,
    )
    return {
        "matched": result.state_hash == branch.current_state_hash,
        "state_hash": result.state_hash,
        "persisted_hash": branch.current_state_hash,
        "projected_state": project_visible_state(result.state, scenario).model_dump(),
        "recorded_commands": [
            {"type": e["type"], "payload": e["payload"], "logical_tick": e["logical_tick"]}
            for e in result.state.ledger
        ],
    }


@router.get("/runs/{run_id}/compare")
async def compare(
    run_id: UUID,
    left: UUID,
    right: UUID,
    auth: Auth = Depends(current_auth),
    db: AsyncSession = Depends(get_db),
):
    result = []
    for bid in (left, right):
        branch, run, scenario = await owned_branch(db, auth.id, bid)
        if run.id != run_id:
            raise unavailable()
        score = await db.scalar(select(ScorecardRecord).where(ScorecardRecord.branch_id == bid))
        result.append(
            {
                "branch": state_view(branch, run, scenario).model_dump(mode="json"),
                "scorecard": score.criteria_json if score else None,
                "divergence_checkpoint": str(branch.source_checkpoint_id)
                if branch.source_checkpoint_id
                else None,
                "actions": [
                    {"type": e["type"], "logical_tick": e["logical_tick"]}
                    for e in parse_state(branch).ledger
                ],
            }
        )
    return {"left": result[0], "right": result[1]}
