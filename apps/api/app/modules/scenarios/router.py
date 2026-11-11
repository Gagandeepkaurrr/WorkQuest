from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import unavailable
from app.db.sessions import get_db
from app.modules.scenarios.models import ScenarioRecord
from app.modules.scenarios.schemas import MissionList, MissionView

router = APIRouter(tags=["missions"])


def public_mission(row: ScenarioRecord):
    return {
        "id": str(row.id),
        "slug": row.slug,
        "version_id": str(row.active_published_version_id),
        **row.public_metadata,
    }


@router.get("/missions", response_model=MissionList)
async def missions(
    q: str = Query("", max_length=100),
    difficulty: str = Query("", max_length=30),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(ScenarioRecord)
            .where(
                ScenarioRecord.archived_at.is_(None),
                ScenarioRecord.active_published_version_id.is_not(None),
            )
            .order_by(ScenarioRecord.slug)
        )
    ).all()
    filtered = [
        public_mission(r)
        for r in rows
        if (not q or q.lower() in str(r.public_metadata).lower())
        and (not difficulty or r.public_metadata["difficulty"] == difficulty)
    ]
    return {
        "items": filtered[offset : offset + limit],
        "next_offset": offset + limit if offset + limit < len(filtered) else None,
    }


@router.get("/missions/{slug}", response_model=MissionView)
async def briefing(slug: str, db: AsyncSession = Depends(get_db)):
    row = await db.scalar(
        select(ScenarioRecord).where(
            ScenarioRecord.slug == slug,
            ScenarioRecord.archived_at.is_(None),
            ScenarioRecord.active_published_version_id.is_not(None),
        )
    )
    if not row:
        raise unavailable()
    return public_mission(row)
