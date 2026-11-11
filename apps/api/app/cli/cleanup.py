"""Run hourly. No learner activity is removed except expired demo accounts."""

import asyncio
from datetime import timedelta

from sqlalchemy import delete, or_

from app.core.security import now
from app.db import models  # noqa: F401
from app.db.sessions import Session
from app.jobs.models import AIJob
from app.modules.auth.models import AuthSession, AuthToken, Outbox, SecretPayload, User


async def cleanup():
    counts = {}
    async with Session.begin() as db:
        terminal = ~AIJob.status.in_(["queued", "running"])
        for job in (
            await db.scalars(
                __import__("sqlalchemy")
                .select(AIJob)
                .where(terminal, AIJob.created_at < now() - timedelta(days=7))
            )
        ).all():
            job.eligible_context_private_json = None
        for name, statement in [
            ("expired_demos", delete(User).where(User.demo_expires_at <= now())),
            (
                "delivery_secrets",
                delete(SecretPayload).where(
                    or_(SecretPayload.expires_at <= now(), SecretPayload.destroyed_at.is_not(None))
                ),
            ),
            (
                "expired_sessions",
                delete(AuthSession).where(
                    or_(AuthSession.expires_at <= now(), AuthSession.revoked_at.is_not(None))
                ),
            ),
            (
                "expired_tokens",
                delete(AuthToken).where(
                    or_(AuthToken.expires_at <= now(), AuthToken.used_at.is_not(None))
                ),
            ),
            (
                "old_jobs",
                delete(AIJob).where(terminal, AIJob.created_at < now() - timedelta(days=90)),
            ),
            ("old_outbox", delete(Outbox).where(Outbox.created_at < now() - timedelta(days=90))),
        ]:
            result = await db.execute(statement)
            counts[name] = getattr(result, "rowcount", 0)
    return counts


if __name__ == "__main__":
    print(asyncio.run(cleanup()))
