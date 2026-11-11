from uuid import UUID
from app.engine.types import Metadata
from app.modules.auth.schemas import StrictModel


class MissionView(Metadata):
    id: UUID
    slug: str
    version_id: UUID


class MissionList(StrictModel):
    items: list[MissionView]
    next_offset: int | None
