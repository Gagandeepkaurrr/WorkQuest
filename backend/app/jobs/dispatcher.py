"""PostgreSQL is the queue of record. Broker acknowledgement is not completion."""

import time
from datetime import timedelta
from typing import TypeVar
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.observability import log
from app.core.security import now
from app.db import models  # noqa: F401
from app.db.sessions import SyncSession
from app.jobs.leases import locked_job, sync_coaching_status
from app.jobs.models import AIJob
from app.modules.auth.models import EmailJob, Outbox

Job = TypeVar("Job", AIJob, EmailJob)


def queued(db: Session, model: type[Job], topic: str) -> list[tuple[str, UUID]]:
    query = select(model).where(
        model.status == "queued",
        or_(
            model.last_dispatched_at.is_(None),
            model.last_dispatched_at < now() - timedelta(seconds=10),
        ),
    )
    if model is AIJob:
        query = query.where(or_(AIJob.next_attempt_at.is_(None), AIJob.next_attempt_at <= now()))
    return [(topic, job.id) for job in db.scalars(query.limit(100))]


def recover_once(dispatch: bool = True):
    with SyncSession() as db:
        expired_ids = list(
            db.scalars(
                select(AIJob.id).where(AIJob.status == "running", AIJob.lease_expires_at < now())
            )
        )
    # Preserve owner -> branch -> job lock order, including recovery.
    for jid in expired_ids:
        with SyncSession.begin() as db:
            locked = locked_job(db, jid)
            if not locked:
                continue
            job = locked[0]
            if job.status == "running" and job.lease_expires_at and job.lease_expires_at < now():
                job.status = "queued" if job.attempt_count < 3 else "failed"
                job.failure_code = "LEASE_EXPIRED"
                job.lease_token = None
                job.updated_at = now()
                sync_coaching_status(db, job)
    with SyncSession.begin() as db:
        for email in db.scalars(
            select(EmailJob)
            .where(EmailJob.status == "running", EmailJob.lease_expires_at < now())
            .with_for_update(skip_locked=True)
        ):
            email.status = "queued" if email.attempt_count < 3 else "failed"
            email.lease_token = None
            email.updated_at = now()
        due = queued(db, AIJob, "ai") + queued(db, EmailJob, "email")
    if not dispatch:
        return due
    from app.jobs.celery_app import celery

    for topic, job_id in due:
        try:
            celery.send_task("workquest." + topic, args=[str(job_id)], retry=False)
        except Exception as exc:
            log.warning(
                "broker_dispatch_failed",
                job_id=str(job_id),
                kind=topic,
                error_type=type(exc).__name__,
            )
            continue
        with SyncSession.begin() as db:
            if topic == "ai":
                ai = db.get(AIJob, job_id)
                if ai:
                    ai.last_dispatched_at = now()
            else:
                delivered_email = db.get(EmailJob, job_id)
                if delivered_email:
                    delivered_email.last_dispatched_at = now()
            for row in db.scalars(
                select(Outbox).where(Outbox.topic == topic, Outbox.payload_id == job_id)
            ):
                row.published_at = now()
                row.attempts += 1
    return due


if __name__ == "__main__":
    while True:
        try:
            recover_once()
        except Exception as exc:
            log.error("dispatcher_iteration_failed", error_type=type(exc).__name__)
        time.sleep(2)
