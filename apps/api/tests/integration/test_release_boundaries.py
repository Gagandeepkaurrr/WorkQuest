from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.ai.contracts import ProviderResult, Reply
from app.db.sessions import Session
from app.jobs.leases import claim_ai_job, fail_attempt, publish_ai_result
from app.modules.auth.models import EmailJob, SecretPayload
from tests.integration.test_jobs import message
from tests.integration.test_runs import command, start


async def test_database_rejects_changes_to_immutable_records(client):
    run = await start(client)
    bid = run["active_branch_id"]
    await command(client, bid, "mission.finish", {}, 0)
    for sql, params in [
        (
            "UPDATE scenario_versions SET definition_private_json='{}' WHERE id=:id",
            {"id": run["scenario_version_id"]},
        ),
        ("UPDATE checkpoints SET snapshot_private_json='{}' WHERE branch_id=:id", {"id": bid}),
        ("UPDATE branch_events SET logical_tick=19 WHERE branch_id=:id", {"id": bid}),
        ("UPDATE scorecards SET total_score=99 WHERE branch_id=:id", {"id": bid}),
        ("UPDATE branches SET base_snapshot_private_json='{}' WHERE id=:id", {"id": bid}),
    ]:
        with pytest.raises(DBAPIError):
            async with Session.begin() as db:
                await db.execute(text(sql), params)


async def test_failed_coaching_is_terminal_without_score_mutation(client):
    run = await start(client)
    bid = run["active_branch_id"]
    await command(client, bid, "mission.finish", {}, 0)
    before = (await client.get(f"/api/v1/branches/{bid}/scorecard")).json()
    response = await client.post(
        f"/api/v1/branches/{bid}/coaching/retry", headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 202, response.text
    lease = claim_ai_job(UUID(response.json()["job_id"]))
    assert lease
    fail_attempt(lease.job_id, lease.token, "PROVIDER_REJECTED", False)
    after = (await client.get(f"/api/v1/branches/{bid}/scorecard")).json()
    assert after["coaching_status"] == "failed"
    assert after["deterministic_hash"] == before["deterministic_hash"]
    assert after["total_score"] == before["total_score"]


async def test_deletion_destroys_secrets_and_blocks_late_publication(client):
    run = await start(client)
    job = await message(client, run["active_branch_id"])
    lease = claim_ai_job(UUID(job["job_id"]))
    assert lease
    async with Session() as db:
        secrets = list((await db.scalars(select(EmailJob.secret_payload_id))).all())
    response = await client.request(
        "DELETE",
        "/api/v1/me",
        json={"password": "correct horse battery staple", "confirmation": "DELETE"},
    )
    assert response.status_code == 200, response.text
    assert not publish_ai_result(
        lease.job_id,
        lease.token,
        ProviderResult(reply=Reply(reply_text="Late reply"), provider="local", model="authored-v1"),
    )
    async with Session() as db:
        for sid in secrets:
            secret = await db.get(SecretPayload, sid)
            assert secret is None or (secret.destroyed_at and secret.encrypted_payload == "")
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_job_lock_refreshes_preloaded_branch_after_concurrent_command(client):
    from app.db.sessions import SyncSession
    from app.jobs.leases import locked_job
    from app.modules.runs.models import Branch

    run = await start(client)
    bid = UUID(run["active_branch_id"])
    job = await message(client, str(bid))
    with SyncSession.begin() as db:
        assert db.get(Branch, bid).state_revision == 0
        assert (
            await command(client, str(bid), "checkout.set_flag", {"enabled": False}, 0)
        ).status_code == 200
        locked = locked_job(db, UUID(job["job_id"]))
        assert locked and locked[1].state_revision == 1


async def test_message_failure_rolls_back_event_quota_and_outbox(client, monkeypatch):
    from sqlalchemy import func

    from app.core.errors import AppError
    from app.jobs.models import AIJob, UsageCounter
    from app.modules.auth.models import Outbox
    from app.modules.conversations import router
    from app.modules.runs.models import BranchEvent

    run = await start(client)
    bid = run["active_branch_id"]
    async with Session() as db:
        before = [
            await db.scalar(select(func.count()).select_from(model))
            for model in [BranchEvent, AIJob, UsageCounter, Outbox]
        ]
    original = router.append_event

    async def fail(*args, **kwargs):
        await original(*args, **kwargs)
        raise AppError("DEPENDENCY_UNAVAILABLE", "Injected transactional failure", 503)

    monkeypatch.setattr(router, "append_event", fail)
    result = await client.post(
        f"/api/v1/branches/{bid}/messages",
        json={"teammate_id": "maya", "text": "A question"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert result.status_code == 503
    async with Session() as db:
        after = [
            await db.scalar(select(func.count()).select_from(model))
            for model in [BranchEvent, AIJob, UsageCounter, Outbox]
        ]
    assert after == before
