from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID,uuid4
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.ai.contracts import CharacterContext,ProviderResult
from app.ai.validation import validate_reply
from app.core.config import get_settings
from app.core.security import now
from app.db.sessions import SyncSession
from app.jobs.models import AIJob,CallAttempt,UsageCounter
from app.modules.auth.models import User
from app.modules.runs.models import Branch,BranchEvent,Run
from app.modules.reports.models import ScorecardRecord


@dataclass
class Lease:
    job_id: UUID
    token: UUID
    context: CharacterContext
    kind: str
    provider: str


def locked_job(db,job_id: UUID):
    initial=db.get(AIJob,job_id)
    if not initial:return None
    branch=db.get(Branch,initial.branch_id);run=db.get(Run,branch.run_id) if branch else None
    if not run:return None
    user=db.scalar(select(User).where(User.id==run.owner_id).with_for_update())
    if not user:return None
    branch=db.scalar(select(Branch).where(Branch.id==initial.branch_id).with_for_update())
    job=db.scalar(select(AIJob).where(AIJob.id==job_id).with_for_update().execution_options(populate_existing=True))
    if not job or user.deleted_at or (user.demo_expires_at and user.demo_expires_at<=now()):return None
    return job,branch,run,user


def sync_event(db,branch,kind,payload):
    branch.last_event_seq+=1
    event=BranchEvent(branch_id=branch.id,seq=branch.last_event_seq,type=kind,actor_kind='system',state_revision_after=branch.state_revision,logical_tick=branch.current_state_private_json['simulation_time'],payload_public_json=payload,payload_private_json={})
    db.add(event);db.flush();return event


def context_current(db,job,branch):
    if job.kind=='dialogue':return branch.status=='active' and job.captured_state_revision==branch.state_revision
    score=db.get(ScorecardRecord,job.scorecard_id) if job.scorecard_id else None
    return bool(score and branch.status=='finalized' and score.deterministic_hash==job.captured_scorecard_hash and score.terminal_state_revision==job.captured_state_revision)


def claim_ai_job(job_id: UUID) -> Lease | None:
    settings=get_settings()
    with SyncSession.begin() as db:
        locked=locked_job(db,job_id)
        if not locked:return None
        job,branch,run,user=locked
        if job.status!='queued' or (job.next_attempt_at and job.next_attempt_at>now()):return None
        if job.attempt_count>=settings.job_max_attempts or (now()-job.created_at).total_seconds()>settings.job_max_age_seconds:
            job.status='failed';job.failure_code='ATTEMPTS_EXHAUSTED';return None
        if not context_current(db,job,branch):
            job.status='stale';job.failure_code='JOB_STALE';sync_event(db,branch,'job.stale',{'job_id':str(job.id)});return None
        provider='mock' if run.is_demo or run.is_admin_preview else settings.ai_provider
        if provider=='gemini' and not user.email_verified_at:
            job.status='failed';job.failure_code='EMAIL_VERIFICATION_REQUIRED';return None
        period=now().date().isoformat();scopes=['calls:global',f'calls:user:{user.id}'];counters=[]
        for scope in scopes:
            db.execute(insert(UsageCounter).values(scope=scope,period=period,accepted_requests=0,reserved_requests=0,reserved_tokens=0,measured_tokens=0).on_conflict_do_nothing())
            counters.append(db.scalar(select(UsageCounter).where(UsageCounter.scope==scope,UsageCounter.period==period).with_for_update()))
        token_budget=7200 if job.kind=='debrief' else 6800
        if counters[0].reserved_requests>=settings.ai_global_daily_request_limit or counters[1].reserved_requests>=settings.ai_user_daily_request_limit or counters[0].reserved_tokens+token_budget>settings.ai_global_daily_token_limit:
            job.status='quota_limited';job.failure_code='AI_QUOTA_EXCEEDED';sync_event(db,branch,'job.quota_limited',{'job_id':str(job.id)});return None
        for counter in counters:counter.reserved_requests+=1;counter.reserved_tokens+=token_budget;counter.updated_at=now()
        job.attempt_count+=1;job.status='running';job.lease_token=uuid4();job.lease_expires_at=now()+timedelta(seconds=settings.job_lease_seconds);job.updated_at=now()
        db.add(CallAttempt(job_id=job.id,attempt_number=job.attempt_count,provider=provider,model='authored-v1' if provider=='mock' else settings.ai_model,prompt_version=settings.ai_prompt_version))
        sync_event(db,branch,'job.running',{'job_id':str(job.id),'attempt':job.attempt_count})
        return Lease(job.id,job.lease_token,CharacterContext.model_validate(job.eligible_context_private_json),job.kind,provider)


def publish_ai_result(job_id: UUID,lease_token: UUID,result: ProviderResult) -> bool:
    with SyncSession.begin() as db:
        locked=locked_job(db,job_id)
        if not locked:return False
        job,branch,run,user=locked
        if job.status!='running' or job.lease_token!=lease_token or not job.lease_expires_at or job.lease_expires_at<=now():return False
        attempt=db.scalar(select(CallAttempt).where(CallAttempt.job_id==job.id,CallAttempt.attempt_number==job.attempt_count))
        attempt.finished_at=now();attempt.input_tokens=result.input_tokens;attempt.output_tokens=result.output_tokens
        if result.input_tokens is not None and result.output_tokens is not None:
            measured=result.input_tokens+result.output_tokens;period=attempt.created_at.date().isoformat();budget=7200 if job.kind=='debrief' else 6800
            for scope in ['calls:global',f'calls:user:{user.id}']:
                counter=db.scalar(select(UsageCounter).where(UsageCounter.scope==scope,UsageCounter.period==period).with_for_update())
                if counter:counter.reserved_tokens=max(0,counter.reserved_tokens-budget+measured);counter.measured_tokens+=measured
            attempt.cost_certainty='measured_usage_estimate' if result.provider!='mock' else 'unknown'
        if not context_current(db,job,branch):
            job.status='stale';job.failure_code='JOB_STALE';job.updated_at=now();attempt.outcome='stale';sync_event(db,branch,'job.stale',{'job_id':str(job.id)});return False
        context=CharacterContext.model_validate(job.eligible_context_private_json)
        try:validate_reply(result.reply,context)
        except ValueError:
            job.status='failed';job.failure_code='INVALID_MODEL_RESPONSE';job.updated_at=now();attempt.outcome='invalid';sync_event(db,branch,'job.failed',{'job_id':str(job.id),'code':job.failure_code});return False
        if job.kind=='debrief':
            score=db.get(ScorecardRecord,job.scorecard_id);score.coaching_text=result.reply.reply_text;score.coaching_status='completed'
            event=sync_event(db,branch,'coaching.completed',{'scorecard_id':str(score.id),'job_id':str(job.id)})
        else:
            facts={f.id:f for f in context.facts}
            payload={**result.reply.model_dump(),'teammate_id':context.teammate_id,'job_id':str(job.id),'provider':result.provider,'citations':[{'fact_id':fid,'artifact_id':facts[fid].artifact_id,'text':facts[fid].text} for fid in result.reply.referenced_fact_ids]}
            event=sync_event(db,branch,'message.assistant',payload)
        job.result_event_id=event.id;job.status='completed';job.updated_at=now();attempt.outcome='completed';return True


def fail_attempt(job_id: UUID,token: UUID,code: str,retryable: bool):
    import random
    with SyncSession.begin() as db:
        locked=locked_job(db,job_id)
        if not locked:return
        job,branch,_,_=locked
        if job.status!='running' or job.lease_token!=token:return
        attempt=db.scalar(select(CallAttempt).where(CallAttempt.job_id==job.id,CallAttempt.attempt_number==job.attempt_count))
        attempt.finished_at=now();attempt.outcome=code
        job.failure_code=code;job.updated_at=now()
        if retryable and job.attempt_count<get_settings().job_max_attempts:
            job.status='queued';job.next_attempt_at=now()+timedelta(seconds=2**job.attempt_count+random.uniform(0,2))
        else:job.status='failed'
        sync_event(db,branch,'job.'+job.status,{'job_id':str(job.id),'code':code})
