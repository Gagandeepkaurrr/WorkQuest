from typing import TypeVar

from prometheus_client import Gauge
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import now
from app.db.sessions import Session, engine
from app.jobs.models import AIJob, CallAttempt, UsageCounter
from app.modules.auth.models import EmailJob

queue = Gauge("wq_jobs", "Durable jobs by safe type/status", ["kind", "status"])
oldest = Gauge("wq_oldest_queued_seconds", "Age of oldest unfinished job", ["kind"])
attempts = Gauge(
    "wq_provider_attempts_retained", "Provider outcomes in retained metadata", ["outcome"]
)
usage = Gauge("wq_provider_tokens_today", "Global reserved/measured daily tokens", ["kind"])
streams = Gauge("wq_active_streams", "Active streams; negative means Redis unavailable")
pool = Gauge("wq_database_pool_connections", "API database pool connections", ["kind"])


Job = TypeVar("Job", AIJob, EmailJob)


async def job_metrics(db: AsyncSession, model: type[Job], kind: str):
    for status, count in await db.execute(
        select(model.status, func.count()).group_by(model.status)
    ):
        queue.labels(kind, status).set(count)
    stamp = await db.scalar(
        select(func.min(model.created_at)).where(model.status.in_(["queued", "running"]))
    )
    oldest.labels(kind).set(max(0, (now() - stamp).total_seconds()) if stamp else 0)


async def refresh_metrics():
    queue.clear()
    attempts.clear()
    async with Session() as db:
        await job_metrics(db, AIJob, "ai")
        await job_metrics(db, EmailJob, "email")
        for outcome, count in await db.execute(
            select(CallAttempt.outcome, func.count()).group_by(CallAttempt.outcome)
        ):
            attempts.labels(outcome).set(count)
        row = await db.get(UsageCounter, ("calls:global", now().date().isoformat()))
        usage.labels("reserved").set(row.reserved_tokens if row else 0)
        usage.labels("measured").set(row.measured_tokens if row else 0)
    for name, method in [("checked_out", "checkedout"), ("capacity", "size")]:
        measure = getattr(engine.pool, method, None)
        pool.labels(name).set(measure() if measure else 0)
    settings = get_settings()
    try:
        async with Redis.from_url(settings.redis_url.get_secret_value(), socket_timeout=2) as redis:
            total = 0
            async for key in redis.scan_iter(
                match=f"{settings.redis_namespace}:streams:*", count=100
            ):
                total += max(0, int(await redis.get(key) or 0))
            streams.set(total)
    except Exception:
        streams.set(-1)
