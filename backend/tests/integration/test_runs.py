import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.cli.seed import seed
from app.db.sessions import Session
from app.main import app
from app.modules.runs.models import Branch, CommandRequestRecord
from tests.integration.test_auth import register


async def start(client):
    await seed()
    await register(client)
    missions = (await client.get("/api/v1/missions")).json()["items"]
    r = await client.post(
        "/api/v1/runs",
        json={
            "scenario_version_id": next(m for m in missions if m["slug"] == "checkout-outage")[
                "version_id"
            ]
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def command(client, branch, kind, payload, revision, key=None):
    return await client.post(
        f"/api/v1/branches/{branch}/commands",
        json={"type": kind, "payload": payload, "expected_state_revision": revision},
        headers={"Idempotency-Key": key or str(uuid4())},
    )


async def test_start_hidden_evidence_and_cross_user(client):
    run = await start(client)
    bid = run["active_branch_id"]
    state = (await client.get(f"/api/v1/branches/{bid}/state")).json()
    assert state["state_revision"] == 0
    assert "checkout.config" not in str(state["projected_state"]["artifacts"])
    assert (
        await client.get(f"/api/v1/branches/{bid}/artifacts/checkout.config")
    ).status_code == 404
    r = await command(client, bid, "evidence.open", {"artifact_id": "checkout.logs"}, 0)
    assert r.status_code == 200, r.text
    assert r.json()["projected_state"]["simulation_time"] == 1
    assert (
        "ConfigSchemaError"
        in (await client.get(f"/api/v1/branches/{bid}/artifacts/checkout.logs")).json()["body"]
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Origin": "http://testserver"},
    ) as other:
        await register(other, "other@example.com")
        for path in [
            f"/branches/{bid}/state",
            f"/runs/{run['id']}",
            f"/branches/{bid}/events",
            f"/branches/{bid}/notes",
            f"/branches/{bid}/artifacts",
        ]:
            assert (await other.get("/api/v1" + path)).status_code == 404, path


async def test_parallel_idempotency_and_revision_conflict(client):
    run = await start(client)
    bid = run["active_branch_id"]
    key = str(uuid4())
    a, b = await asyncio.gather(
        command(client, bid, "checkout.set_flag", {"enabled": False}, 0, key),
        command(client, bid, "checkout.set_flag", {"enabled": False}, 0, key),
    )
    assert a.status_code == b.status_code == 200, (a.text, b.text)
    assert a.json() == b.json()
    assert (
        await command(client, bid, "checkout.set_flag", {"enabled": True}, 0, key)
    ).status_code == 409
    a, b = await asyncio.gather(
        command(client, bid, "checkout.restart", {}, 1),
        command(client, bid, "checkout.invalidate_cache", {}, 1),
    )
    assert sorted([a.status_code, b.status_code]) == [200, 409]
    async with Session() as db:
        branch = await db.get(Branch, bid)
        assert branch.state_revision == 2
        assert branch.current_state_private_json["simulation_time"] == 2


async def test_rejected_transition_rolls_back_and_finalize(client):
    run = await start(client)
    bid = run["active_branch_id"]
    r = await command(client, bid, "checkout.publish_config", {}, 0)
    assert r.status_code == 409
    state = (await client.get(f"/api/v1/branches/{bid}/state")).json()
    assert state["state_revision"] == 0 and state["projected_state"]["simulation_time"] == 0
    async with Session() as db:
        assert (
            len(
                (
                    await db.scalars(
                        select(CommandRequestRecord).where(
                            CommandRequestRecord.operation_scope == f"commands:{bid}"
                        )
                    )
                ).all()
            )
            == 0
        )
    from app.engine.registry import load_scenario

    s = load_scenario("checkout-outage")
    commands = [
        {
            "type": "mission.update",
            "payload": {"impact": 30, "status": "impacted", "next_action_id": "evidence.open"},
        },
        *s.golden_commands,
        {"type": "mission.diagnose", "payload": {"cause_id": s.rubric.cause_id}},
        {
            "type": "mission.recap",
            "payload": {"cause_id": s.rubric.cause_id, "outcome": "successful"},
        },
        {"type": "mission.finish", "payload": {}},
    ]
    for revision, cmd in enumerate(commands):
        r = await command(client, bid, cmd["type"], cmd["payload"], revision)
        assert r.status_code == 200, r.text
    score = (await client.get(f"/api/v1/branches/{bid}/scorecard")).json()
    assert score["total_score"] == 100
    assert (await command(client, bid, "checkout.restart", {}, len(commands))).status_code == 409
