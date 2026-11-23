from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.sessions import Session
from app.modules.reports.models import ReportShare
from app.modules.runs.models import CommandRequestRecord
from tests.integration.test_jobs import message
from tests.integration.test_runs import command, start


async def test_checkpoint_fork_preserves_parent_notes_and_context(client):
    run = await start(client)
    bid = run["active_branch_id"]
    await command(client, bid, "evidence.open", {"artifact_id": "checkout.logs"}, 0)
    await client.put(
        f"/api/v1/branches/{bid}/notes",
        json={"body": "Saved early thinking", "expected_revision": 0},
        headers={"Idempotency-Key": str(uuid4())},
    )
    r = await client.post(
        f"/api/v1/branches/{bid}/checkpoints",
        json={"expected_state_revision": 1, "label": "After logs"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 201, r.text
    checkpoint = r.json()["id"]
    await command(client, bid, "evidence.open", {"artifact_id": "checkout.config"}, 1)
    parent = (await client.get(f"/api/v1/branches/{bid}/state")).json()
    r = await client.post(
        f"/api/v1/checkpoints/{checkpoint}/fork",
        json={"label": "Try mitigation first"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 201, r.text
    child = r.json()["branch_id"]
    state = (await client.get(f"/api/v1/branches/{child}/state")).json()
    assert state["state_revision"] == 0 and state["last_event_seq"] == 1 and state["practice_mode"]
    assert state["projected_state"]["simulation_time"] == 1
    assert (await client.get(f"/api/v1/branches/{child}/notes")).json()[
        "body"
    ] == "Saved early thinking"
    assert (
        await client.get(f"/api/v1/branches/{child}/artifacts/checkout.config")
    ).status_code == 404
    assert (await client.get(f"/api/v1/branches/{bid}/state")).json() == parent
    await command(client, child, "checkout.set_flag", {"enabled": False}, 0)
    replay = (await client.get(f"/api/v1/branches/{child}/replay")).json()
    assert replay["matched"]
    assert (await client.get(f"/api/v1/branches/{bid}/state")).json() == parent


async def test_checkpoint_pending_dialogue_and_secret_share_replay(client):
    run = await start(client)
    bid = run["active_branch_id"]
    job = await message(client, bid)
    r = await client.post(
        f"/api/v1/branches/{bid}/checkpoints",
        json={"expected_state_revision": 0, "label": "Pending"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 409, r.text
    await client.post(
        f"/api/v1/jobs/{job['job_id']}/cancel", headers={"Idempotency-Key": str(uuid4())}
    )
    await command(client, bid, "mission.finish", {}, 0)
    key = str(uuid4())
    body = {"alias": "Alex", "expiry_days": 7}
    a = await client.post(
        f"/api/v1/branches/{bid}/shares", json=body, headers={"Idempotency-Key": key}
    )
    b = await client.post(
        f"/api/v1/branches/{bid}/shares", json=body, headers={"Idempotency-Key": key}
    )
    assert a.status_code == b.status_code == 201, (a.text, b.text)
    assert a.json() == b.json()
    token = a.json()["url"].rsplit("/", 1)[-1]
    report = (await client.get("/api/v1/shared-reports/" + token)).json()
    assert "owner_id" not in report and "chat" not in str(report) and "email" not in str(report)
    async with Session() as db:
        record = await db.scalar(
            select(CommandRequestRecord).where(CommandRequestRecord.idempotency_key == UUID(key))
        )
        assert token not in str(record.response_json)
        share = await db.get(ReportShare, UUID(a.json()["share_id"]))
        assert token != share.token_digest
    assert (await client.delete("/api/v1/shares/" + a.json()["share_id"])).status_code == 200
    assert (await client.get("/api/v1/shared-reports/" + token)).status_code == 404
