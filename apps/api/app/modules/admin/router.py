from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import Auth, admin_auth
from app.core.errors import AppError, unavailable
from app.core.security import canonical_hash, now
from app.db.sessions import get_db
from app.engine.types import Scenario
from app.engine.validation import validate_scenario
from app.jobs.models import AIJob, CallAttempt, UsageCounter
from app.modules.admin.models import AdminAudit
from app.modules.auth.models import EmailJob
from app.modules.auth.schemas import StrictModel
from app.modules.runs.service import create_run
from app.modules.scenarios.models import ScenarioRecord, ScenarioVersion

router = APIRouter(prefix="/admin", tags=["administration"])


class DraftInput(StrictModel):
    definition: Scenario
    draft_revision: int = Field(ge=0)


class ImportInput(StrictModel):
    definition: Scenario


def version_view(v):
    return {
        "id": str(v.id),
        "scenario_id": str(v.scenario_id),
        "version_number": v.version_number,
        "status": v.status,
        "draft_revision": v.draft_revision,
        "content_hash": v.content_hash,
        "validated_hash": v.validated_hash,
        "validation_report": v.validation_report,
        "definition": v.definition_private_json,
    }


def audit(db, request, auth, operation, target, hash=None):
    db.add(
        AdminAudit(
            actor_id=auth.id,
            operation=operation,
            target_id=target,
            content_hash=hash,
            request_id=request.state.request_id,
        )
    )


async def get_version(db, id, lock=False):
    query = select(ScenarioVersion).where(ScenarioVersion.id == id)
    if lock:
        scenario_id = await db.scalar(
            select(ScenarioVersion.scenario_id).where(ScenarioVersion.id == id)
        )
        if scenario_id is None:
            raise unavailable()
        await db.scalar(
            select(ScenarioRecord).where(ScenarioRecord.id == scenario_id).with_for_update()
        )
        query = query.with_for_update().execution_options(populate_existing=True)
    version = await db.scalar(query)
    if not version:
        raise unavailable()
    return version


@router.get("/scenarios")
async def scenarios(auth: Auth = Depends(admin_auth), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(ScenarioRecord).order_by(ScenarioRecord.slug).limit(100))).all()
    items = []
    for row in rows:
        versions = (
            await db.scalars(
                select(ScenarioVersion)
                .where(ScenarioVersion.scenario_id == row.id)
                .order_by(ScenarioVersion.version_number.desc())
            )
        ).all()
        items.append(
            {
                "id": str(row.id),
                "slug": row.slug,
                "title": row.public_metadata["title"],
                "archived": bool(row.archived_at),
                "active_version_id": str(row.active_published_version_id),
                "versions": [
                    {"id": str(v.id), "version": v.version_number, "status": v.status}
                    for v in versions
                ],
            }
        )
    return {"items": items}


@router.post("/scenarios", status_code=201)
@router.post("/scenarios/import", status_code=201)
async def import_definition(
    body: ImportInput,
    request: Request,
    auth: Auth = Depends(admin_auth),
    db: AsyncSession = Depends(get_db),
):
    definition = body.definition
    data = definition.model_dump()
    existing = await db.scalar(select(ScenarioRecord).where(ScenarioRecord.slug == definition.slug))
    if existing:
        raise AppError(
            "VALIDATION_ERROR", "This slug already exists. Create a new draft version instead.", 409
        )
    row = ScenarioRecord(
        slug=definition.slug, public_metadata=definition.metadata.model_dump(), created_by=auth.id
    )
    db.add(row)
    await db.flush()
    version = ScenarioVersion(
        scenario_id=row.id,
        version_number=1,
        status="draft",
        mechanics_id=definition.mechanics_id,
        definition_private_json=data,
        content_hash=canonical_hash(data),
        created_by=auth.id,
    )
    db.add(version)
    await db.flush()
    audit(db, request, auth, "scenario.import", version.id, version.content_hash)
    await db.commit()
    return version_view(version)


@router.post("/scenarios/{scenario_id}/versions", status_code=201)
async def new_version(
    scenario_id: UUID,
    request: Request,
    auth: Auth = Depends(admin_auth),
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(
        select(ScenarioRecord).where(ScenarioRecord.id == scenario_id).with_for_update()
    )
    if not row:
        raise unavailable()
    latest = await db.scalar(
        select(ScenarioVersion)
        .where(ScenarioVersion.scenario_id == scenario_id)
        .order_by(ScenarioVersion.version_number.desc())
        .limit(1)
    )
    assert latest is not None
    data = {**latest.definition_private_json, "content_version": latest.version_number + 1}
    version = ScenarioVersion(
        scenario_id=scenario_id,
        version_number=latest.version_number + 1,
        status="draft",
        mechanics_id=latest.mechanics_id,
        definition_private_json=data,
        content_hash=canonical_hash(data),
        created_by=auth.id,
    )
    db.add(version)
    await db.flush()
    audit(db, request, auth, "version.create", version.id, version.content_hash)
    await db.commit()
    return version_view(version)


@router.get("/scenario-versions/{version_id}")
@router.get("/scenario-versions/{version_id}/export")
async def read_version(
    version_id: UUID, auth: Auth = Depends(admin_auth), db: AsyncSession = Depends(get_db)
):
    return version_view(await get_version(db, version_id))


@router.put("/scenario-versions/{version_id}")
async def edit_version(
    version_id: UUID,
    body: DraftInput,
    request: Request,
    auth: Auth = Depends(admin_auth),
    db: AsyncSession = Depends(get_db),
):
    version = await get_version(db, version_id, True)
    if version.status != "draft":
        raise AppError(
            "PRECONDITION_FAILED",
            "Published definitions are immutable. Create a new draft version.",
            409,
        )
    if version.draft_revision != body.draft_revision:
        raise AppError(
            "STALE_REVISION", "This draft changed. Reload and compare before saving.", 409
        )
    row = await db.get(ScenarioRecord, version.scenario_id)
    assert row is not None
    if (
        body.definition.slug != row.slug
        or body.definition.content_version != version.version_number
        or body.definition.mechanics_id != version.mechanics_id
    ):
        raise AppError(
            "VALIDATION_ERROR",
            "Scenario identity, version and mechanics cannot change within a draft.",
            422,
        )
    version.definition_private_json = body.definition.model_dump()
    version.content_hash = canonical_hash(version.definition_private_json)
    version.draft_revision += 1
    version.validated_hash = None
    version.validation_report = None
    audit(db, request, auth, "version.edit", version.id, version.content_hash)
    await db.commit()
    return version_view(version)


@router.post("/scenario-versions/{version_id}/validate")
async def validate(
    version_id: UUID,
    request: Request,
    auth: Auth = Depends(admin_auth),
    db: AsyncSession = Depends(get_db),
):
    version = await get_version(db, version_id, True)
    report = validate_scenario(version.definition_private_json)
    if version.status == "draft":
        version.validation_report = report.model_dump()
        version.validated_hash = report.content_hash if report.passed else None
    audit(db, request, auth, "version.validate", version.id, report.content_hash)
    await db.commit()
    return report


@router.post("/scenario-versions/{version_id}/preview", status_code=201)
async def preview(
    version_id: UUID, auth: Auth = Depends(admin_auth), idempotency_key: UUID = Header()
):
    return await create_run(auth.id, version_id, idempotency_key, preview=True)


@router.post("/scenario-versions/{version_id}/publish")
async def publish(
    version_id: UUID,
    request: Request,
    auth: Auth = Depends(admin_auth),
    db: AsyncSession = Depends(get_db),
):
    version = await get_version(db, version_id, True)
    if (
        version.status != "draft"
        or version.validated_hash != version.content_hash
        or not version.validation_report
        or not version.validation_report["passed"]
    ):
        raise AppError(
            "PRECONDITION_FAILED", "Validate the current draft hash before publication.", 409
        )
    report = validate_scenario(version.definition_private_json)
    if not report.passed:
        raise AppError("PRECONDITION_FAILED", "Scenario checks no longer pass.", 409)
    row = await db.scalar(
        select(ScenarioRecord).where(ScenarioRecord.id == version.scenario_id).with_for_update()
    )
    assert row is not None
    version.status = "published"
    version.published_at = now()
    row.active_published_version_id = version.id
    row.public_metadata = version.definition_private_json["metadata"]
    row.archived_at = None
    audit(db, request, auth, "version.publish", version.id, version.content_hash)
    await db.commit()
    return {"published": True, "version_id": str(version.id)}


@router.post("/scenarios/{scenario_id}/archive")
async def archive(
    scenario_id: UUID,
    request: Request,
    auth: Auth = Depends(admin_auth),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(ScenarioRecord, scenario_id)
    if not row:
        raise unavailable()
    row.archived_at = now()
    audit(db, request, auth, "scenario.archive", row.id)
    await db.commit()
    return {"archived": True}


@router.get("/operations")
async def operations(auth: Auth = Depends(admin_auth), db: AsyncSession = Depends(get_db)):
    jobs = {
        status: count
        for status, count in (
            await db.execute(select(AIJob.status, func.count()).group_by(AIJob.status))
        ).all()
    }
    emails = {
        status: count
        for status, count in (
            await db.execute(select(EmailJob.status, func.count()).group_by(EmailJob.status))
        ).all()
    }
    oldest = await db.scalar(
        select(func.min(AIJob.created_at)).where(AIJob.status.in_(["queued", "running"]))
    )
    usage = (
        await db.scalars(
            select(UsageCounter)
            .where(UsageCounter.scope == "calls:global")
            .order_by(UsageCounter.period.desc())
            .limit(7)
        )
    ).all()
    return {
        "ai_jobs": jobs,
        "email_jobs": emails,
        "oldest_queued_age_seconds": int((now() - oldest).total_seconds()) if oldest else 0,
        "provider_attempts": await db.scalar(select(func.count()).select_from(CallAttempt)),
        "daily_usage": [
            {
                "period": u.period,
                "provider_calls_reserved": u.reserved_requests,
                "tokens_reserved": u.reserved_tokens,
                "tokens_measured": u.measured_tokens,
            }
            for u in usage
        ],
    }
