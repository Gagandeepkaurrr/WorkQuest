from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.engine.types import WorldState
from app.modules.checkpoints.models import Checkpoint
from app.modules.runs.models import Branch,BranchEvent,LearnerNote
from app.modules.runs.repository import event_view


async def capture_checkpoint(db: AsyncSession,branch: Branch,label: str) -> Checkpoint:
    notes=await db.get(LearnerNote,branch.id)
    prefix=list(branch.base_snapshot_private_json.get('prefix',[]))
    events=(await db.scalars(select(BranchEvent).where(BranchEvent.branch_id==branch.id).order_by(BranchEvent.seq))).all()
    prefix += [event_view(e) for e in events if e.payload_public_json is not None]
    state=WorldState.model_validate(branch.current_state_private_json)
    snapshot={'state':state.model_dump(),'notes':{'body':notes.body if notes else '','revision':notes.revision if notes else 0},'prefix':prefix}
    checkpoint=Checkpoint(branch_id=branch.id,label=label,source_state_revision=branch.state_revision,source_event_seq=branch.last_event_seq,state_hash=state.canonical_hash(),snapshot_private_json=snapshot,display_prefix_json=prefix)
    db.add(checkpoint)
    await db.flush()
    return checkpoint
