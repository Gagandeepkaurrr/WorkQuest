from uuid import UUID,uuid4
from datetime import timedelta
from sqlalchemy import select
from app.db.sessions import Session
from app.core.security import now
from app.jobs.models import AIJob,CallAttempt,UsageCounter
from app.jobs.leases import claim_ai_job,publish_ai_result
from app.ai.contracts import Reply,ProviderResult
from app.jobs.dispatcher import recover_once
from tests.integration.test_runs import start,command

async def message(client,bid,text='What should I investigate?'):
    r=await client.post(f'/api/v1/branches/{bid}/messages',json={'teammate_id':'maya','text':text},headers={'Idempotency-Key':str(uuid4())})
    assert r.status_code==202,r.text
    return r.json()

async def test_stale_fencing_and_cancelled_publication(client):
    run=await start(client);bid=run['active_branch_id'];job=await message(client,bid)
    lease=claim_ai_job(UUID(job['job_id']))
    assert lease and claim_ai_job(UUID(job['job_id'])) is None
    await command(client,bid,'checkout.set_flag',{'enabled':False},0)
    assert publish_ai_result(lease.job_id,lease.token,ProviderResult(reply=Reply(reply_text='Current evidence is limited.'),provider='mock',model='authored-v1')) is False
    async with Session() as db:assert (await db.get(AIJob,lease.job_id)).status=='stale'
    job=await message(client,bid);lease=claim_ai_job(UUID(job['job_id']))
    r=await client.post(f'/api/v1/jobs/{job["job_id"]}/cancel',headers={'Idempotency-Key':str(uuid4())})
    assert r.status_code==200,r.text
    assert not publish_ai_result(lease.job_id,lease.token,ProviderResult(reply=Reply(reply_text='No late reply.'),provider='mock',model='authored-v1'))

async def test_lease_expiry_and_lost_broker_ack_recovery(client):
    run=await start(client);job=await message(client,run['active_branch_id']);jid=UUID(job['job_id'])
    lease=claim_ai_job(jid)
    async with Session.begin() as db:
        row=await db.get(AIJob,jid);row.lease_expires_at=now()-timedelta(seconds=1)
    recover_once(dispatch=False)
    fresh=claim_ai_job(jid)
    assert fresh and fresh.token!=lease.token
    assert not publish_ai_result(jid,lease.token,ProviderResult(reply=Reply(reply_text='Late'),provider='mock',model='authored-v1'))
    assert publish_ai_result(jid,fresh.token,ProviderResult(reply=Reply(reply_text='Current'),provider='mock',model='authored-v1'))
    assert not publish_ai_result(jid,fresh.token,ProviderResult(reply=Reply(reply_text='Duplicate'),provider='mock',model='authored-v1'))
    async with Session() as db:
        attempts=(await db.scalars(select(CallAttempt).where(CallAttempt.job_id==jid))).all()
        assert len(attempts)==2

async def test_quota_and_schema_failure_preserve_work(client):
    run=await start(client);bid=run['active_branch_id'];job=await message(client,bid)
    lease=claim_ai_job(UUID(job['job_id']))
    assert not publish_ai_result(lease.job_id,lease.token,ProviderResult(reply=Reply(reply_text='bad reference',referenced_fact_ids=['unrevealed']),provider='mock',model='authored-v1'))
    assert (await client.get(f'/api/v1/branches/{bid}/state')).status_code==200
    assert (await command(client,bid,'checkout.set_flag',{'enabled':False},0)).status_code==200
