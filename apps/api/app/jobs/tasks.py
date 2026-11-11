from uuid import UUID

from app.ai.contracts import Provider
from app.ai.providers.local import LocalProvider
from app.db import models  # noqa: F401
from app.jobs.celery_app import celery
from app.jobs.email import deliver_email
from app.jobs.leases import claim_ai_job, fail_attempt, publish_ai_result


@celery.task(name="workquest.ai")
def execute_ai(job_id: str):
    lease = claim_ai_job(UUID(job_id))
    if not lease:
        return
    try:
        provider: Provider = LocalProvider()
        result = (
            provider.debrief_coaching(lease.context)
            if lease.kind == "debrief"
            else provider.character_reply(lease.context)
        )
        publish_ai_result(lease.job_id, lease.token, result)
    except Exception as exc:
        retryable = isinstance(exc, (TimeoutError, ConnectionError, OSError))
        # No raw exception/provider payload enters logs, broker messages or learner output.
        fail_attempt(
            lease.job_id,
            lease.token,
            "PROVIDER_TEMPORARY" if retryable else "PROVIDER_REJECTED",
            retryable,
        )


@celery.task(name="workquest.email")
def execute_email(job_id: str):
    deliver_email(UUID(job_id))
