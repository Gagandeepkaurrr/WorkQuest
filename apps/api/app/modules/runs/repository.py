from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError, unavailable
from app.core.security import canonical_hash, now
from app.engine.types import Scenario, WorldState
from app.modules.auth.models import User
from app.modules.runs.models import Branch, BranchEvent, CommandRequestRecord, Run
from app.modules.scenarios.models import ScenarioVersion


async def lock_owner(db: AsyncSession,owner_id: UUID) -> User:
    user=await db.scalar(select(User).where(User.id==owner_id).with_for_update())
    if not user or user.deleted_at or (user.demo_expires_at and user.demo_expires_at<=now()):raise unavailable()
    return user


async def owned_run(db: AsyncSession,owner_id: UUID,run_id: UUID) -> Run:
    run=await db.scalar(select(Run).where(Run.id==run_id,Run.owner_id==owner_id))
    if not run:raise unavailable()
    return run


async def owned_branch(db: AsyncSession,owner_id: UUID,branch_id: UUID,lock=False) -> tuple[Branch,Run,Scenario]:
    query=select(Branch).join(Run,Run.id==Branch.run_id).where(Branch.id==branch_id,Run.owner_id==owner_id)
    if lock:query=query.with_for_update(of=Branch)
    branch=await db.scalar(query)
    if not branch:raise unavailable()
    run=await db.get(Run,branch.run_id)
    version=await db.get(ScenarioVersion,run.scenario_version_id)
    definition=run.preview_definition_private_json if run.is_admin_preview else version.definition_private_json
    return branch,run,Scenario.model_validate(definition)


async def idempotent_record(db: AsyncSession,owner_id: UUID,scope: str,key: UUID,body: dict):
    # Caller holds owner lock; it serializes duplicate keys and first-attempt assignment.
    hashed=canonical_hash({'scope':scope,'body':body})
    existing=await db.scalar(select(CommandRequestRecord).where(CommandRequestRecord.user_id==owner_id,CommandRequestRecord.operation_scope==scope,CommandRequestRecord.idempotency_key==key))
    if existing:
        if existing.request_hash!=hashed:raise AppError('IDEMPOTENCY_CONFLICT','This request key was used for different input.',409)
        return existing,True
    record=CommandRequestRecord(user_id=owner_id,operation_scope=scope,idempotency_key=key,request_hash=hashed)
    db.add(record)
    await db.flush()
    return record,False


def event_view(event: BranchEvent) -> dict:
    return {'id':str(event.id),'seq':event.seq,'type':event.type,'logical_tick':event.logical_tick,'state_revision':event.state_revision_after,'payload':event.payload_public_json,'created_at':event.created_at.isoformat()}


async def append_event(db: AsyncSession,branch: Branch,kind: str,payload: dict | None,owner_id: UUID | None=None,private: dict | None=None,event_id: UUID | None=None,command_id: UUID | None=None):
    branch.last_event_seq+=1
    kwargs={'id':event_id} if event_id else {}
    event=BranchEvent(**kwargs,branch_id=branch.id,seq=branch.last_event_seq,type=kind,actor_id=owner_id,actor_kind='learner' if owner_id else 'system',command_id=command_id,state_revision_after=branch.state_revision,logical_tick=branch.current_state_private_json['simulation_time'],payload_public_json=payload,payload_private_json=private or {})
    db.add(event)
    await db.flush()
    return event


def assert_revision(branch: Branch,expected: int):
    if branch.state_revision!=expected:raise AppError('STALE_REVISION','The simulation changed. Review the refreshed state before trying again.',409)


def parse_state(branch: Branch) -> WorldState:return WorldState.model_validate(branch.current_state_private_json)
