from uuid import UUID

from app.engine.types import Scorecard


class ReportView(Scorecard):
    id: UUID
    branch_id: UUID
    run_id: UUID
    title: str
    version: int
    created_at: str
    practice_mode: bool
    is_demo: bool
    is_admin_preview: bool
    coaching_status: str
    coaching_text: str | None
