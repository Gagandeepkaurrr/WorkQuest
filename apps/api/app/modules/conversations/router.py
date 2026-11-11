import asyncio
import json
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import Field
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import build_character_context
from app.api.contracts import ConversationView, JobView
from app.api.dependencies import Auth, authenticate, current_auth
from app.core.config import get_settings
from app.core.errors import AppError, unavailable
from app.core.security import canonical_hash, now
from app.db.sessions import Session, get_db
from app.jobs.models import AIJob, UsageCounter
from app.modules.auth.models import Outbox
from app.modules.auth.schemas import StrictModel
from app.modules.runs.models import BranchEvent
from app.modules.runs.repository import (
    append_event,
    event_view,
    idempotent_record,
    lock_owner,
    owned_branch,
    parse_state,
)

router = APIRouter(tags=["conversations"])


class MessageInput(StrictModel):
    teammate_id: str = Field(max_length=30)
    text: str = Field(min_length=1, max_length=4000)


async def transcript_events(db, branch, teammate_id):
    prefix = branch.base_snapshot_private_json.get("prefix", [])
    events = (
        await db.scalars(
            select(BranchEvent)
            .where(
                BranchEvent.branch_id == branch.id,
                BranchEvent.type.in_(["message.user", "message.assistant"]),
            )
            .order_by(BranchEvent.seq)
        )
    ).all()
    return [
        e
        for e in prefix + [event_view(e) for e in events]
        if e["type"] in ("message.user", "message.assistant")
        and e["payload"].get("teammate_id") == teammate_id
    ]


def context_transcript(events):
    return [
        {
            "role": "assistant" if e["type"] == "message.assistant" else "user",
            "text": e["payload"].get("reply_text", e["payload"].get("text", "")),
        }
        for e in events
    ]


def job_view(job: AIJob):
    return {
        "id": str(job.id),
        "job_id": str(job.id),
        "kind": job.kind,
        "status": job.status,
        "attempt_count": job.attempt_count,
        "failure_code": job.failure_code,
        "captured_state_revision": job.captured_state_revision,
        "created_at": job.created_at.isoformat(),
        "retry_available": job.status in ("failed", "stale", "cancelled", "quota_limited")
        and job.attempt_count < get_settings().job_max_attempts,
    }


@router.get("/branches/{branch_id}/conversations/{teammate_id}", response_model=ConversationView)
async def conversation(
    branch_id: UUID,
    teammate_id: str,
    auth: Auth = Depends(current_auth),
    db: AsyncSession = Depends(get_db),
):
    branch, _, scenario = await owned_branch(db, auth.id, branch_id)
    if teammate_id not in {t.id for t in scenario.teammates}:
        raise unavailable()
    jobs = (
        await db.scalars(
            select(AIJob)
            .where(AIJob.branch_id == branch_id, AIJob.kind == "dialogue")
            .order_by(AIJob.created_at.desc())
            .limit(20)
        )
    ).all()
    return {
        "items": await transcript_events(db, branch, teammate_id),
        "jobs": [
            job_view(j)
            for j in jobs
            if j.eligible_context_private_json
            and j.eligible_context_private_json.get("teammate_id") == teammate_id
        ],
    }


@router.post("/branches/{branch_id}/messages", status_code=202)
async def send_message(
    branch_id: UUID,
    body: MessageInput,
    auth: Auth = Depends(current_auth),
    idempotency_key: UUID = Header(),
):
    if not body.text.strip():
        raise AppError("VALIDATION_ERROR", "Write a question first.", 422)
    async with Session.begin() as db:
        await lock_owner(db, auth.id)
        branch, run, scenario = await owned_branch(db, auth.id, branch_id, lock=True)
        record, repeated = await idempotent_record(
            db, auth.id, f"messages:{branch_id}", idempotency_key, body.model_dump()
        )
        if repeated:
            return record.response_json
        if branch.status != "active":
            raise AppError("PRECONDITION_FAILED", "Conversation requires an active branch.", 409)
        settings = get_settings()
        active = await db.scalar(
            select(AIJob.id).where(
                AIJob.branch_id == branch_id,
                AIJob.kind == "dialogue",
                AIJob.status.in_(["queued", "running"]),
            )
        )
        if active:
            raise AppError("AI_BUSY", "Wait for the current reply or cancel it.", 409)
        count = await db.scalar(
            select(func.count())
            .select_from(AIJob)
            .where(AIJob.branch_id == branch_id, AIJob.kind == "dialogue")
        )
        if (count or 0) >= settings.ai_branch_request_limit:
            raise AppError(
                "AI_QUOTA_EXCEEDED",
                "This branch has reached its conversation limit. Investigation and scoring remain available.",
                429,
            )
        scope = f"accepted:user:{auth.id}"
        period = now().date().isoformat()
        await db.execute(
            insert(UsageCounter)
            .values(
                scope=scope,
                period=period,
                accepted_requests=0,
                reserved_requests=0,
                reserved_tokens=0,
                measured_tokens=0,
            )
            .on_conflict_do_nothing()
        )
        counter = await db.get(UsageCounter, (scope, period))
        assert counter is not None  # Insert/upsert above holds the owner lock.
        if counter.accepted_requests >= settings.ai_user_daily_request_limit:
            raise AppError(
                "AI_QUOTA_EXCEEDED",
                "Daily conversation limit reached. Deterministic work remains available.",
                429,
            )
        backlog = await db.scalar(
            select(func.count()).select_from(AIJob).where(AIJob.status.in_(["queued", "running"]))
        )
        if (backlog or 0) >= 1000:
            raise AppError(
                "AI_UNAVAILABLE",
                "The conversation queue is full. Try later; your investigation can continue.",
                503,
            )
        transcript = await transcript_events(db, branch, body.teammate_id)
        context = build_character_context(
            parse_state(branch),
            scenario,
            body.teammate_id,
            context_transcript(transcript),
            body.text.strip(),
        )
        event = await append_event(
            db,
            branch,
            "message.user",
            {"teammate_id": body.teammate_id, "text": body.text.strip()},
            auth.id,
        )
        job = AIJob(
            branch_id=branch_id,
            request_event_id=event.id,
            captured_state_revision=branch.state_revision,
            captured_event_seq=branch.last_event_seq,
            eligible_context_private_json=context.model_dump(),
            input_hash=canonical_hash(context.model_dump()),
        )
        db.add(job)
        await db.flush()
        db.add(Outbox(topic="ai", payload_id=job.id))
        counter.accepted_requests += 1
        await append_event(
            db, branch, "job.queued", {"job_id": str(job.id), "teammate_id": body.teammate_id}
        )
        record.response_status = 202
        record.response_json = {
            "job_id": str(job.id),
            "message_event_id": str(event.id),
            "captured_revision": branch.state_revision,
            "status_url": f"/api/v1/jobs/{job.id}",
            "status": "queued",
        }
        return record.response_json


@router.get("/jobs/{job_id}", response_model=JobView)
async def get_job(
    job_id: UUID, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    job = await db.get(AIJob, job_id)
    if not job:
        raise unavailable()
    await owned_branch(db, auth.id, job.branch_id)
    return job_view(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobView)
@router.post("/jobs/{job_id}/retry", response_model=JobView)
async def job_operation(
    job_id: UUID,
    request: Request,
    auth: Auth = Depends(current_auth),
    idempotency_key: UUID = Header(),
):
    operation = request.url.path.rsplit("/", 1)[-1]
    async with Session.begin() as db:
        await lock_owner(db, auth.id)
        job = await db.get(AIJob, job_id)
        if not job:
            raise unavailable()
        branch, _, scenario = await owned_branch(db, auth.id, job.branch_id, lock=True)
        record, repeated = await idempotent_record(
            db, auth.id, f"job:{job_id}:{operation}", idempotency_key, {}
        )
        if repeated:
            return record.response_json
        if operation == "cancel":
            if job.status in ("queued", "running"):
                job.status = "cancelled"
                job.lease_token = None
                job.updated_at = now()
        else:
            if not job_view(job)["retry_available"]:
                raise AppError("PRECONDITION_FAILED", "This job cannot be retried.", 409)
            if job.kind != "dialogue":
                raise AppError(
                    "PRECONDITION_FAILED", "Use the coaching retry on the assessment.", 409
                )
            if branch.status != "active":
                raise AppError("PRECONDITION_FAILED", "Resume the branch before retrying.", 409)
            pending = await db.scalar(
                select(AIJob.id).where(
                    AIJob.branch_id == branch.id,
                    AIJob.kind == "dialogue",
                    AIJob.status.in_(["queued", "running"]),
                )
            )
            if pending:
                raise AppError("AI_BUSY", "Another reply is already in progress.", 409)
            old = job.eligible_context_private_json
            if not old:
                raise AppError(
                    "RESULT_EXPIRED", "The retained context has expired. Send a new question.", 409
                )
            transcript = await transcript_events(db, branch, old["teammate_id"])
            context = build_character_context(
                parse_state(branch),
                scenario,
                old["teammate_id"],
                context_transcript(transcript),
                old["message"],
            )
            job.eligible_context_private_json = context.model_dump()
            job.input_hash = canonical_hash(context.model_dump())
            job.captured_state_revision = branch.state_revision
            job.captured_event_seq = branch.last_event_seq
            job.status = "queued"
            job.next_attempt_at = None
            job.last_dispatched_at = None
            job.failure_code = None
            job.updated_at = now()
            db.add(Outbox(topic="ai", payload_id=job.id))
        await append_event(db, branch, "job." + job.status, {"job_id": str(job.id)})
        record.response_json = job_view(job)
        return record.response_json


def parse_cursor(value: str, branch_id: UUID) -> int:
    try:
        branch, seq = value.rsplit(":", 1)
        if UUID(branch) != branch_id or int(seq) < 0:
            raise ValueError
        return int(seq)
    except ValueError:
        raise AppError(
            "VALIDATION_ERROR", "The event cursor belongs to a different or invalid stream.", 422
        ) from None


@router.get("/branches/{branch_id}/stream")
async def stream(
    branch_id: UUID,
    request: Request,
    cursor: str | None = None,
    auth: Auth = Depends(current_auth),
    db: AsyncSession = Depends(get_db),
):
    branch, _, _ = await owned_branch(db, auth.id, branch_id)
    after = parse_cursor(
        request.headers.get("last-event-id") or cursor or f"{branch_id}:0", branch_id
    )
    if after > branch.last_event_seq:
        raise AppError("VALIDATION_ERROR", "The event cursor is ahead of this branch.", 422)
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url.get_secret_value(), socket_timeout=2)
    key = f"{settings.redis_namespace}:streams:{auth.id}"
    try:
        count = await redis.eval(
            "local n=redis.call('INCR',KEYS[1]);redis.call('EXPIRE',KEYS[1],45);return n", 1, key
        )
        if count > 3:
            await redis.decr(key)
            await redis.aclose()
            raise AppError(
                "RATE_LIMITED", "Close another live workspace before opening this stream.", 429
            )
    except AppError:
        raise
    except Exception:
        await redis.aclose()
        raise AppError(
            "DEPENDENCY_UNAVAILABLE",
            "Live updates are unavailable. Snapshot polling remains available.",
            503,
        ) from None

    async def generate():
        nonlocal after
        heartbeat = time.monotonic()
        try:
            while not await request.is_disconnected():
                try:
                    async with Session() as session:
                        await authenticate(request, session, csrf=False)
                        await owned_branch(session, auth.id, branch_id)
                        rows = (
                            await session.scalars(
                                select(BranchEvent)
                                .where(BranchEvent.branch_id == branch_id, BranchEvent.seq > after)
                                .order_by(BranchEvent.seq)
                                .limit(100)
                            )
                        ).all()
                        for event in rows:
                            after = event.seq
                            if event.payload_public_json is not None:
                                yield f"id: {branch_id}:{after}\nevent: update\ndata: {json.dumps(event_view(event))}\n\n"
                        if rows:
                            yield f'id: {branch_id}:{after}\nevent: cursor\ndata: {{"cursor":"{branch_id}:{after}"}}\n\n'
                except AppError:
                    break
                if time.monotonic() - heartbeat >= 15:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic()
                    try:
                        await redis.expire(key, 45)
                    except Exception:
                        pass
                await asyncio.sleep(1)
        finally:
            try:
                await redis.decr(key)
            except Exception:
                pass
            await redis.aclose()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )
