"""Twenty isolated learners for five minutes; built-in teammates, never a production database."""
import argparse, asyncio, json, os, platform, secrets, statistics, subprocess, sys, time
from pathlib import Path
from uuid import uuid4
import httpx, psycopg
from dotenv import dotenv_values
root=Path(__file__).resolve().parent.parent
(root/'artifacts').mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=300);parser.add_argument('--learners',type=int,default=20);args=parser.parse_args()
if not 1<=args.learners<=20 or not 5<=args.seconds<=300:parser.error('Bounded to 1–20 learners and 5–300 seconds')
env={**os.environ,**{k:v for k,v in dotenv_values(root/'.env').items() if v is not None}}
base=env['DATABASE_URL'].rsplit('/',1)[0];name='workquest_load_'+secrets.token_hex(4)
admin_url=(base+'/postgres').replace('postgresql+psycopg://','postgresql://')
with psycopg.connect(admin_url,autocommit=True) as db:db.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(name)))
env.update(DATABASE_URL=base+'/'+name,APP_ENV='local',APP_ORIGIN='http://localhost:8001',REDIS_NAMESPACE=name,AI_PROVIDER='local',DEMO_ENABLED='false')
os.environ.update(env);sys.path.insert(0,str(root/'apps/api'))
children=[];logs=[];measurements={'reads':[],'commands':[]};errors=[];calls=0
try:
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=root/'apps/api',env=env,check=True)
    from app.cli.seed import seed
    from app.db.sessions import SyncSession
    from app.modules.auth.models import User
    from app.core.security import now,password_hasher
    asyncio.run(seed())
    password=secrets.token_urlsafe(20)
    with SyncSession.begin() as db:
        for i in range(args.learners):db.add(User(normalized_email=f'load-{i}@example.com',display_name=f'Load {i}',password_hash=password_hasher.hash(password),email_verified_at=now()))
    for label,command in [('api',[sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001','--no-access-log']),('worker',[sys.executable,'-m','celery','-A','app.jobs.celery_app:celery','worker','--pool=solo','--loglevel=ERROR','--without-gossip','--without-mingle']),('dispatcher',[sys.executable,'-m','app.jobs.dispatcher'])]:
        output=(root/'artifacts'/f'load-{label}.log').open('w');logs.append(output)
        children.append(subprocess.Popen(command,cwd=root/'apps/api',env=env,stdout=output,stderr=subprocess.STDOUT))
    for _ in range(50):
        try:
            if httpx.get('http://localhost:8001/health/ready',timeout=2).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(.2)
    async def learner(index):
        global calls
        async with httpx.AsyncClient(base_url='http://localhost:8001',headers={'Origin':'http://localhost:8001'},timeout=20) as client:
            async def request(method,path,body=None,kind=None):
                global calls
                started=time.perf_counter()
                response=await client.request(method,'/api/v1'+path,json=body,headers={'Idempotency-Key':str(uuid4())})
                calls+=1
                if kind:measurements[kind].append((time.perf_counter()-started)*1000)
                if response.status_code>=400:errors.append({'status':response.status_code,'route':path.split('/')[1]});raise RuntimeError('Unexpected API response')
                return response.json()
            await request('POST','/auth/login',{'email':f'load-{index}@example.com','password':password})
            csrf=await request('GET','/auth/csrf');client.headers['X-CSRF-Token']=csrf['csrf_token']
            missions=await request('GET','/missions');vid=next(m['version_id'] for m in missions['items'] if m['slug']=='checkout-outage')
            async def newrun():
                run=await request('POST','/runs',{'scenario_version_id':vid});return run['active_branch_id']
            bid=await newrun();revision=0
            await request('POST',f'/branches/{bid}/messages',{'teammate_id':'maya','text':'What evidence is available?'})
            deadline=time.monotonic()+args.seconds
            step=0
            while time.monotonic()<deadline:
                if step%2==0:
                    world=await request('GET',f'/branches/{bid}/state',kind='reads')
                    revision=world['state_revision']
                    if world['status']=='finalized':bid=await newrun();revision=0
                else:
                    result=await request('POST',f'/branches/{bid}/commands',{'type':'checkout.set_flag','payload':{'enabled':(step//2)%2==0},'expected_state_revision':revision},kind='commands')
                    revision=result['state_revision']
                step+=1
                await asyncio.sleep(1)
    async def exercise():
        outcomes=await asyncio.gather(*(learner(i) for i in range(args.learners)),return_exceptions=True)
        for result in outcomes:
            if isinstance(result,Exception):errors.append({'exception':type(result).__name__})
    started=time.monotonic();asyncio.run(exercise());elapsed=time.monotonic()-started
    def summary(values):
        ordered=sorted(values)
        return {'count':len(values),'p50_ms':round(statistics.median(values),2),'p95_ms':round(ordered[int((len(ordered)-1)*.95)],2),'max_ms':round(max(values),2)} if values else {'count':0}
    with psycopg.connect(env['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')) as db:
        dataset={table:db.execute(psycopg.sql.SQL('SELECT count(*) FROM {}').format(psycopg.sql.Identifier(table))).fetchone()[0] for table in ['users','runs','branches','branch_events','scorecards','ai_jobs']}
    report={'host':platform.platform(),'processor':subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip() if sys.platform=='darwin' else platform.processor(),'memory_bytes':subprocess.check_output(['sysctl','-n','hw.memsize'],text=True).strip() if sys.platform=='darwin' else 'not measured','learners':args.learners,'requested_seconds':args.seconds,'elapsed_seconds':round(elapsed,2),'ordinary_workload':'alternating state reads and costed flag commands, one request/second/learner; new run after logical cap','ai':'one local dialogue per learner; no external model','dataset':dataset,'requests':calls,'unexpected_errors':errors,'reads':summary(measurements['reads']),'commands':summary(measurements['commands']),'concurrent_work':'local browser/build/verification tasks may run on same host','targets_met':not errors and all(summary(v).get('p95_ms',9999)<500 for v in measurements.values())}
    (root/'artifacts/load-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
    for child in children:child.terminate()
    for child in children:
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait()
    for output in logs:output.close()
    with psycopg.connect(admin_url,autocommit=True) as db:
        db.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()',(name,))
        db.execute(psycopg.sql.SQL('DROP DATABASE {}').format(psycopg.sql.Identifier(name)))
if errors:raise SystemExit(1)
