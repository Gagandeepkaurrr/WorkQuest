from uuid import UUID
from fastapi import APIRouter,Depends,Header,Query,Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import Auth,current_auth
from app.core.errors import AppError,unavailable
from app.core.security import now
from app.db.sessions import get_db,Session
from app.engine.types import Scenario
from app.engine.visibility import available_artifacts
from app.modules.reports.models import ScorecardRecord
from app.modules.reports.schemas import ReportView
from app.modules.runs.models import Branch,BranchEvent,CommandRequestRecord,LearnerNote,Run
from app.modules.runs.repository import assert_revision,event_view,idempotent_record,lock_owner,owned_branch,owned_run,parse_state
from app.modules.runs.schemas import BranchState,CommandResponse,NoteInput,RevisionInput,StartRun,WorldCommandRequest
from app.modules.runs.service import create_run,execute_world_command,run_view,state_view
from app.modules.scenarios.models import ScenarioVersion

router=APIRouter(tags=['runs'])


@router.post('/runs',status_code=201)
async def start(body: StartRun,auth: Auth=Depends(current_auth),idempotency_key: UUID=Header()):
    return await create_run(auth.id,body.scenario_version_id,idempotency_key)


@router.get('/runs')
async def runs(auth: Auth=Depends(current_auth),limit: int=Query(20,ge=1,le=100),offset: int=Query(0,ge=0),db: AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(Run).where(Run.owner_id==auth.id).order_by(Run.created_at.desc()).offset(offset).limit(limit))).all()
    items=[]
    for run in rows:
        version=await db.get(ScenarioVersion,run.scenario_version_id)
        scenario=Scenario.model_validate(run.preview_definition_private_json or version.definition_private_json)
        branch=await db.get(Branch,run.active_branch_id)
        items.append({**run_view(run,scenario),'status':branch.status,'simulation_time':branch.current_state_private_json['simulation_time'],'practice_mode':branch.practice_mode})
    return {'items':items,'next_offset':offset+limit if len(items)==limit else None}


@router.get('/runs/{run_id}')
async def run_detail(run_id: UUID,auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    run=await owned_run(db,auth.id,run_id)
    _,_,scenario=await owned_branch(db,auth.id,run.active_branch_id)
    return run_view(run,scenario)


@router.post('/runs/{run_id}/archive')
async def archive(run_id: UUID,auth: Auth=Depends(current_auth),idempotency_key: UUID=Header()):
    async with Session.begin() as db:
        await lock_owner(db,auth.id);run=await owned_run(db,auth.id,run_id)
        record,repeated=await idempotent_record(db,auth.id,f'archive:{run_id}',idempotency_key,{})
        if repeated:return record.response_json
        run.archived_at=now();record.response_json={'archived':True}
        return record.response_json


@router.get('/branches/{branch_id}/state',response_model=BranchState)
async def state(branch_id: UUID,auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    branch,run,scenario=await owned_branch(db,auth.id,branch_id)
    return state_view(branch,run,scenario)


@router.post('/branches/{branch_id}/commands',response_model=CommandResponse)
async def command(branch_id: UUID,body: WorldCommandRequest,auth: Auth=Depends(current_auth),idempotency_key: UUID=Header()):
    return await execute_world_command(auth.id,branch_id,idempotency_key,body)


@router.get('/branches/{branch_id}/commands/{command_id}')
async def command_status(branch_id: UUID,command_id: UUID,auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    await owned_branch(db,auth.id,branch_id)
    record=await db.scalar(select(CommandRequestRecord).where(CommandRequestRecord.user_id==auth.id,CommandRequestRecord.operation_scope==f'commands:{branch_id}',(CommandRequestRecord.id==command_id)|(CommandRequestRecord.idempotency_key==command_id)))
    if not record:raise unavailable()
    return record.response_json


@router.get('/branches/{branch_id}/events')
async def events(branch_id: UUID,after: int=Query(0,ge=0),limit: int=Query(100,ge=1,le=100),auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    branch,_,_=await owned_branch(db,auth.id,branch_id)
    rows=(await db.scalars(select(BranchEvent).where(BranchEvent.branch_id==branch_id,BranchEvent.seq>after,BranchEvent.seq<=branch.last_event_seq).order_by(BranchEvent.seq).limit(limit))).all()
    return {'items':[event_view(e) for e in rows if e.payload_public_json is not None],'cursor':f'{branch_id}:{rows[-1].seq if rows else after}','last_event_seq':branch.last_event_seq,'inherited_prefix':branch.base_snapshot_private_json.get('prefix',[]) if after==0 else []}


@router.get('/branches/{branch_id}/artifacts')
async def artifacts(branch_id: UUID,q: str=Query('',max_length=100),auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    branch,run,scenario=await owned_branch(db,auth.id,branch_id)
    world=parse_state(branch)
    items=[a.model_dump() for a in state_view(branch,run,scenario).projected_state.artifacts]
    if q:
        safe_bodies={a.id:a.body for a in available_artifacts(world,scenario) if a.id in world.opened}
        items=[a for a in items if q.lower() in (a['title']+' '+safe_bodies.get(a['id'],'')).lower()]
    return {'items':items}


@router.get('/branches/{branch_id}/artifacts/{artifact_id}')
async def artifact(branch_id: UUID,artifact_id: str,auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    branch,_,scenario=await owned_branch(db,auth.id,branch_id);world=parse_state(branch)
    a=next((a for a in available_artifacts(world,scenario) if a.id==artifact_id and a.id in world.opened),None)
    if not a:raise unavailable()
    return {'id':a.id,'title':a.title,'type':a.type,'body':a.body,'label':'Historical incident evidence · t=0'}


@router.get('/branches/{branch_id}/notes')
async def notes(branch_id: UUID,auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    await owned_branch(db,auth.id,branch_id);note=await db.get(LearnerNote,branch_id)
    return {'body':note.body,'revision':note.revision}


@router.put('/branches/{branch_id}/notes')
async def save_note(branch_id: UUID,body: NoteInput,auth: Auth=Depends(current_auth),idempotency_key: UUID=Header()):
    async with Session.begin() as db:
        await lock_owner(db,auth.id);await owned_branch(db,auth.id,branch_id,lock=True)
        record,repeated=await idempotent_record(db,auth.id,f'notes:{branch_id}',idempotency_key,body.model_dump())
        if repeated:return record.response_json
        note=await db.get(LearnerNote,branch_id)
        if note.revision!=body.expected_revision:raise AppError('STALE_REVISION','Your saved notes changed. Compare before replacing them.',409)
        note.body=body.body;note.revision+=1;note.updated_at=now()
        record.response_json={'body':note.body,'revision':note.revision};return record.response_json


@router.get('/branches/{branch_id}/scorecard',response_model=ReportView)
async def scorecard(branch_id: UUID,auth: Auth=Depends(current_auth),db: AsyncSession=Depends(get_db)):
    branch,run,scenario=await owned_branch(db,auth.id,branch_id)
    score=await db.scalar(select(ScorecardRecord).where(ScorecardRecord.branch_id==branch_id))
    if not score:raise unavailable()
    return {**score.criteria_json,'id':str(score.id),'branch_id':str(branch_id),'run_id':str(run.id),'title':scenario.metadata.title,'version':scenario.content_version,'created_at':score.created_at.isoformat(),'practice_mode':branch.practice_mode,'is_demo':run.is_demo,'is_admin_preview':run.is_admin_preview,'coaching_status':score.coaching_status,'coaching_text':score.coaching_text}


@router.post('/branches/{branch_id}/pause')
@router.post('/branches/{branch_id}/resume')
async def lifecycle(branch_id: UUID,request: Request,body: RevisionInput,auth: Auth=Depends(current_auth),idempotency_key: UUID=Header()):
    operation=request.url.path.rsplit('/',1)[-1]
    async with Session.begin() as db:
        await lock_owner(db,auth.id);branch,run,scenario=await owned_branch(db,auth.id,branch_id,lock=True)
        record,repeated=await idempotent_record(db,auth.id,f'{operation}:{branch_id}',idempotency_key,body.model_dump())
        if repeated:return record.response_json
        assert_revision(branch,body.expected_state_revision)
        if branch.status=='finalized':raise AppError('BRANCH_FINALIZED','This branch has ended.',409)
        branch.status='paused' if operation=='pause' else 'active'
        record.response_json=state_view(branch,run,scenario).model_dump(mode='json')
        return record.response_json
