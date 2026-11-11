"""Restore a local snapshot into a generated disposable DB; never overwrite a target."""
from pathlib import Path
import asyncio,json,os,secrets,subprocess,sys,tempfile,time
from dotenv import dotenv_values
import psycopg
root=Path(__file__).resolve().parent.parent
(root/'artifacts').mkdir(exist_ok=True)
settings={k:v for k,v in dotenv_values(root/'.env').items() if v is not None}
if settings.get('APP_ENV')!='local':raise SystemExit('Local rehearsal only')
base=settings['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://').rsplit('/',1)[0]
name='workquest_restore_'+secrets.token_hex(4);previous='workquest_upgrade_'+secrets.token_hex(4)
created=[];started=time.monotonic()
try:
    with psycopg.connect(base+'/postgres',autocommit=True) as db:
        for target in [name,previous]:db.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(target)));created.append(target)
    env={**os.environ,**settings,'DATABASE_URL':settings['DATABASE_URL'].rsplit('/',1)[0]+'/'+previous,'APP_ENV':'local'}
    subprocess.run([sys.executable,'-m','alembic','upgrade','38e51082aa0b'],cwd=root/'apps/api',env=env,check=True)
    subprocess.run([sys.executable,'-m','app.cli.seed'],cwd=root/'apps/api',env=env,check=True)
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=root/'apps/api',env=env,check=True)
    subprocess.run([sys.executable,'-m','app.cli.seed'],cwd=root/'apps/api',env=env,check=True)
    with psycopg.connect(base+'/'+previous) as db:assert db.execute('SELECT count(*) FROM scenario_versions').fetchone()[0]==3
    with tempfile.TemporaryFile() as backup:
        subprocess.run(['docker','compose','exec','-T','db','pg_dump','-U','workquest','-Fc','workquest'],cwd=root,stdout=backup,check=True)
        backup.seek(0)
        subprocess.run(['docker','compose','exec','-T','db','pg_restore','-U','workquest','--no-owner','--exit-on-error','-d',name],cwd=root,stdin=backup,check=True)
    # Counts are compared to the snapshot itself, not a live source changing under browser tests.
    with psycopg.connect(base+'/'+name) as db:
        tables=[row[0] for row in db.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")]
        counts={table:db.execute(psycopg.sql.SQL('SELECT count(*) FROM {}').format(psycopg.sql.Identifier(table))).fetchone()[0] for table in tables}
        assert counts['scenario_versions']>=3 and counts['checkpoints']>0 and counts['branches']>0
        sys.path.insert(0,str(root/'apps/api'))
        from app.engine.replay import replay_branch
        from app.engine.types import Scenario,WorldState,canonical_hash
        for definition,content_hash in db.execute('SELECT definition_private_json,content_hash FROM scenario_versions'):
            assert canonical_hash(definition)==content_hash
        replayed=0
        for baseline,current,expected,definition in db.execute('SELECT b.base_snapshot_private_json,b.current_state_private_json,b.current_state_hash,CASE WHEN r.is_admin_preview THEN r.preview_definition_private_json ELSE v.definition_private_json END FROM branches b JOIN runs r ON r.id=b.run_id JOIN scenario_versions v ON v.id=r.scenario_version_id'):
            result=replay_branch(WorldState.model_validate(baseline['state']),current['ledger'],Scenario.model_validate(definition))
            assert result.state_hash==expected;replayed+=1
        for snapshot,expected in db.execute('SELECT snapshot_private_json,state_hash FROM checkpoints'):
            assert WorldState.model_validate(snapshot['state']).canonical_hash()==expected
        version=db.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    report={'result':'PASS','restored_schema':version,'tables':counts,'replayed_branches':replayed,'checkpoint_hashes_checked':counts['checkpoints'],'fresh_migration_and_previous_fixture_upgrade':'PASS; 38e51082aa0b seeded twice, then upgraded','elapsed_seconds':round(time.monotonic()-started,2),'storage':'local temporary backup automatically deleted; production encrypted offsite restore not verified'}
    (root/'artifacts/restore-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
    with psycopg.connect(base+'/postgres',autocommit=True) as db:
        for target in created:
            db.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()',(target,))
            db.execute(psycopg.sql.SQL('DROP DATABASE {}').format(psycopg.sql.Identifier(target)))
