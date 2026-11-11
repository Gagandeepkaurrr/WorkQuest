import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from starlette.requests import Request

from app.ai.contracts import ProviderResult, Reply
from app.api.dependencies import authenticate
from app.cli.seed import seed
from app.core.config import get_settings
from app.core.security import now
from app.db.sessions import Session
from app.jobs.celery_app import celery
from app.jobs.dispatcher import recover_once
from app.jobs.leases import claim_ai_job, fail_attempt, publish_ai_result
from app.jobs.models import AIJob, CallAttempt, UsageCounter
from app.main import app
from app.modules.auth.models import AuthSession, Outbox, SecretPayload
from app.modules.conversations.router import parse_cursor, stream
from app.modules.reports.models import ReportShare
from app.modules.runs.models import Branch, LearnerProgress
from app.modules.runs.repository import append_event
from app.modules.scenarios.models import ScenarioRecord, ScenarioVersion
from tests.integration.test_auth import register
from tests.integration.test_jobs import message
from tests.integration.test_runs import command, start


async def test_first_attempt_simultaneous_roots_and_seed_idempotence(client):
    run = await start(client)
    await seed()
    async with Session.begin() as db:
        assert await db.scalar(select(func.count()).select_from(ScenarioRecord)) == 3
        assert await db.scalar(select(func.count()).select_from(ScenarioVersion)) == 3
        await db.execute(__import__("sqlalchemy").delete(LearnerProgress))
    body = {"scenario_version_id": run["scenario_version_id"]}
    key = str(uuid4())
    a, b, c = await asyncio.gather(
        *[
            client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": k})
            for k in [key, key, str(uuid4())]
        ]
    )
    assert a.status_code == b.status_code == c.status_code == 201
    assert a.json() == b.json()
    branches = [
        (await client.get(f"/api/v1/branches/{r.json()['active_branch_id']}/state")).json()
        for r in [a, c]
    ]
    assert sorted(b["practice_mode"] for b in branches) == [False, True]
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(LearnerProgress)) == 1


async def test_ownership_for_nested_resources_and_draft_rules(client):
    run = await start(client)
    bid = run["active_branch_id"]
    job = await message(client, bid)
    await client.post(
        f"/api/v1/jobs/{job['job_id']}/cancel", headers={"Idempotency-Key": str(uuid4())}
    )
    cp = (await client.get(f"/api/v1/branches/{bid}/checkpoints")).json()["items"][0]["id"]
    await command(client, bid, "mission.finish", {}, 0)
    share = (
        await client.post(
            f"/api/v1/branches/{bid}/shares", json={}, headers={"Idempotency-Key": str(uuid4())}
        )
    ).json()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Origin": "http://testserver"},
    ) as other:
        await register(other, "different@example.com")
        for path in [
            f"/branches/{bid}/checkpoints",
            f"/branches/{bid}/replay",
            f"/branches/{bid}/scorecard",
            f"/branches/{bid}/conversations/maya",
            f"/jobs/{job['job_id']}",
            f"/runs/{run['id']}/branches",
            f"/runs/{run['id']}/compare?left={bid}&right={bid}",
        ]:
            assert (await other.get("/api/v1" + path)).status_code == 404, path
        for path, body in [
            (f"/checkpoints/{cp}/fork", {"label": "Guess"}),
            (f"/branches/{bid}/shares", {}),
            (f"/branches/{bid}/coaching/retry", {}),
            (f"/jobs/{job['job_id']}/retry", {}),
        ]:
            assert (
                await other.post(
                    "/api/v1" + path, json=body, headers={"Idempotency-Key": str(uuid4())}
                )
            ).status_code == 404, path
        assert (await other.delete(f"/api/v1/shares/{share['share_id']}")).status_code == 404
    async with Session.begin() as db:
        version = await db.get(ScenarioVersion, UUID(run["scenario_version_id"]))
        draft = ScenarioVersion(
            scenario_id=version.scenario_id,
            version_number=2,
            status="draft",
            mechanics_id=version.mechanics_id,
            definition_private_json=version.definition_private_json,
            content_hash=version.content_hash,
        )
        db.add(draft)
        await db.flush()
        draft_id = draft.id
        scenario = await db.get(ScenarioRecord, version.scenario_id)
        scenario.archived_at = now()
    for vid in [draft_id, run["scenario_version_id"]]:
        assert (
            await client.post(
                "/api/v1/runs",
                json={"scenario_version_id": str(vid)},
                headers={"Idempotency-Key": str(uuid4())},
            )
        ).status_code == 404
    assert (await client.get(f"/api/v1/branches/{bid}/scorecard")).status_code == 200


async def test_broker_ack_is_not_completion_and_payload_is_id_only(client, monkeypatch):
    run = await start(client)
    job = await message(client, run["active_branch_id"])
    calls = []
    monkeypatch.setattr(celery, "send_task", lambda name, **kw: calls.append((name, kw)))
    recover_once()
    assert ("workquest.ai", {"args": [job["job_id"]], "retry": False}) in calls
    calls.clear()
    async with Session.begin() as db:
        row = await db.get(AIJob, UUID(job["job_id"]))
        row.last_dispatched_at = now() - timedelta(seconds=11)
        assert (await db.scalar(select(Outbox).where(Outbox.payload_id == row.id))).published_at
        for secret in (await db.scalars(select(SecretPayload))).all():
            assert (
                "token" not in secret.encrypted_payload
                and "example.com" not in secret.encrypted_payload
            )
    recover_once()
    assert ("workquest.ai", {"args": [job["job_id"]], "retry": False}) in calls


async def test_every_retry_and_coaching_reserves_quota(client, monkeypatch):
    run = await start(client)
    bid = run["active_branch_id"]
    job = await message(client, bid)
    jid = UUID(job["job_id"])
    lease = claim_ai_job(jid)
    assert lease
    fail_attempt(jid, lease.token, "PROVIDER_TEMPORARY", True)
    async with Session.begin() as db:
        (await db.get(AIJob, jid)).next_attempt_at = now() - timedelta(seconds=1)
    second = claim_ai_job(jid)
    assert second
    fail_attempt(jid, second.token, "PROVIDER_REJECTED", False)
    await command(client, bid, "mission.finish", {}, 0)
    coaching = (
        await client.post(
            f"/api/v1/branches/{bid}/coaching/retry", headers={"Idempotency-Key": str(uuid4())}
        )
    ).json()
    coach = claim_ai_job(UUID(coaching["job_id"]))
    assert coach
    assert publish_ai_result(
        coach.job_id,
        coach.token,
        ProviderResult(
            reply=Reply(reply_text="Review the deterministic assessment."),
            provider="mock",
            model="authored-v1",
        ),
    )
    async with Session() as db:
        global_usage = await db.get(UsageCounter, ("calls:global", now().date().isoformat()))
        assert (
            global_usage.reserved_requests == 3 and global_usage.reserved_tokens == 6800 * 2 + 7200
        )
        assert await db.scalar(select(func.count()).select_from(CallAttempt)) == 3
    monkeypatch.setattr(get_settings(), "ai_global_daily_request_limit", 3)
    response = await client.post(
        f"/api/v1/branches/{bid}/coaching/retry", headers={"Idempotency-Key": str(uuid4())}
    )
    blocked = UUID(response.json()["job_id"])
    assert claim_ai_job(blocked) is None
    async with Session() as db:
        assert (await db.get(AIJob, blocked)).status == "quota_limited"
        assert await db.scalar(select(func.count()).select_from(CallAttempt)) == 3
    assert (await client.get(f"/api/v1/branches/{bid}/scorecard")).status_code == 200


async def test_sse_private_cursor_reconnect_and_revocation(client):
    run = await start(client)
    bid = UUID(run["active_branch_id"])
    async with Session.begin() as db:
        branch = await db.get(Branch, bid)
        await append_event(db, branch, "private.only", None, private={"secret": "hidden"})
        await append_event(db, branch, "public.marker", {"text": "permitted"})
        await append_event(db, branch, "private.last", None)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/api/v1/branches/{bid}/stream",
            "headers": [
                (b"cookie", ("; ".join(f"{k}={v}" for k, v in client.cookies.items())).encode())
            ],
        }
    )
    request.is_disconnected = AsyncMock(return_value=False)
    async with Session() as db:
        auth = await authenticate(request, db)
        response = await stream(bid, request, str(bid) + ":3", auth, db)
    iterator = response.body_iterator
    first = await anext(iterator)
    cursor = await anext(iterator)
    assert "permitted" in first and "hidden" not in first and f"{bid}:5" in first
    assert f"{bid}:6" in cursor
    await iterator.aclose()
    with pytest.raises(Exception):
        parse_cursor(f"{uuid4()}:0", bid)
    async with Session.begin() as db:
        branch = await db.get(Branch, bid)
        await append_event(db, branch, "public.new", {"text": "reconnected"})
    async with Session() as db:
        response = await stream(bid, request, f"{bid}:6", auth, db)
    iterator = response.body_iterator
    assert "reconnected" in await anext(iterator)
    await anext(iterator)
    async with Session.begin() as db:
        await db.execute(
            update(AuthSession).where(AuthSession.id == auth.session.id).values(revoked_at=now())
        )
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(iterator), timeout=3)


async def test_replay_has_no_external_dispatch_and_share_expiry(client, monkeypatch):
    run = await start(client)
    bid = run["active_branch_id"]
    await command(client, bid, "checkout.set_flag", {"enabled": False}, 0)

    def forbidden(*args, **kwargs):
        raise AssertionError("Replay attempted external execution")

    monkeypatch.setattr(celery, "send_task", forbidden)
    from app.ai.providers.mock import MockProvider

    monkeypatch.setattr(MockProvider, "character_reply", forbidden)
    import smtplib

    monkeypatch.setattr(smtplib.SMTP, "send_message", forbidden)
    assert (await client.get(f"/api/v1/branches/{bid}/replay")).json()["matched"]
    await command(client, bid, "mission.finish", {}, 1)
    key = str(uuid4())
    path = f"/api/v1/branches/{bid}/shares"
    share = (await client.post(path, json={}, headers={"Idempotency-Key": key})).json()
    token = share["url"].rsplit("/", 1)[1]
    async with Session.begin() as db:
        (await db.get(ReportShare, UUID(share["share_id"]))).expires_at = now() - timedelta(
            seconds=1
        )
        for secret in (
            await db.scalars(select(SecretPayload).where(SecretPayload.purpose == "share_replay"))
        ).all():
            secret.expires_at = now() - timedelta(seconds=1)
    assert (await client.get(f"/api/v1/shared-reports/{token}")).status_code == 404
    retry = await client.post(path, json={}, headers={"Idempotency-Key": key})
    assert retry.status_code == 409 and retry.json()["error"]["code"] == "RESULT_EXPIRED"
