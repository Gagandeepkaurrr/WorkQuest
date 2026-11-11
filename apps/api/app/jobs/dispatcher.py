"""PostgreSQL is the queue of record. Broker acknowledgement is not completion."""
import time
from datetime import timedelta
from sqlalchemy import or_,select
from app.db import models  # noqa: F401
from app.core.security import now
from app.db.sessions import SyncSession
from app.jobs.models import AIJob
from app.modules.auth.models import EmailJob,Outbox


def recover_once(dispatch: bool=True):
    due=[]
    with SyncSession.begin() as db:
        for model,topic in [(AIJob,'ai'),(EmailJob,'email')]:
            expired=db.scalars(select(model).where(model.status=='running',model.lease_expires_at<now()).with_for_update(skip_locked=True)).all()
            for job in expired:
                job.status='queued' if job.attempt_count<3 else 'failed';job.lease_token=None;job.updated_at=now()
            query=select(model).where(model.status=='queued',or_(model.last_dispatched_at.is_(None),model.last_dispatched_at<now()-timedelta(seconds=10)))
            if model is AIJob:query=query.where(or_(model.next_attempt_at.is_(None),model.next_attempt_at<=now()))
            for job in db.scalars(query.limit(100).with_for_update(skip_locked=True)):
                due.append((topic,job.id))
    if not dispatch:return due
    from app.jobs.celery_app import celery
    for topic,job_id in due:
        try:celery.send_task('workquest.'+topic,args=[str(job_id)],retry=False)
        except Exception:continue
        with SyncSession.begin() as db:
            model=AIJob if topic=='ai' else EmailJob
            job=db.get(model,job_id)
            if job:job.last_dispatched_at=now()
            for row in db.scalars(select(Outbox).where(Outbox.topic==topic,Outbox.payload_id==job_id)):
                row.published_at=now();row.attempts+=1
    return due


if __name__=='__main__':
    while True:
        try:recover_once()
        except Exception:pass  # Operational health exposes queue age; never print SQL containing secrets.
        time.sleep(2)
