from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.sessions import Session
from app.modules.auth.models import User
from app.modules.runs.models import Run
from tests.integration.test_runs import start


async def test_admin_hash_bound_validation_preview_and_immutable_publish(client):
    await start(client)
    assert (await client.get("/api/v1/admin/scenarios")).status_code == 403
    async with Session.begin() as db:
        user = await db.scalar(select(User).where(User.normalized_email == "learner@example.com"))
        user.role = "admin"
    scenarios = (await client.get("/api/v1/admin/scenarios")).json()["items"]
    s = next(x for x in scenarios if x["slug"] == "checkout-outage")
    r = await client.post(f"/api/v1/admin/scenarios/{s['id']}/versions")
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    draft = (await client.get("/api/v1/admin/scenario-versions/" + vid)).json()
    validation = await client.post(f"/api/v1/admin/scenario-versions/{vid}/validate")
    assert validation.status_code == 200 and validation.json()["passed"], validation.text
    preview = await client.post(
        f"/api/v1/admin/scenario-versions/{vid}/preview", headers={"Idempotency-Key": str(uuid4())}
    )
    assert preview.status_code == 201, preview.text
    definition = draft["definition"]
    definition["metadata"]["title"] = "An edited draft title"
    r = await client.put(
        f"/api/v1/admin/scenario-versions/{vid}",
        json={"definition": definition, "draft_revision": 0},
    )
    assert r.status_code == 200, r.text
    assert (await client.post(f"/api/v1/admin/scenario-versions/{vid}/publish")).status_code == 409
    async with Session() as db:
        run = await db.get(Run, UUID(preview.json()["id"]))
        assert run.preview_definition_private_json["metadata"]["title"] != "An edited draft title"
    assert (await client.post(f"/api/v1/admin/scenario-versions/{vid}/validate")).json()["passed"]
    assert (await client.post(f"/api/v1/admin/scenario-versions/{vid}/publish")).status_code == 200
    # Routine deployments seed authored v1 without replacing an administrator's v2.
    from app.cli.seed import seed
    from app.modules.scenarios.models import ScenarioRecord

    await seed()
    async with Session() as db:
        scenario = await db.get(ScenarioRecord, UUID(s["id"]))
        assert scenario.active_published_version_id == UUID(vid)
    assert (
        await client.put(
            f"/api/v1/admin/scenario-versions/{vid}",
            json={"definition": definition, "draft_revision": 1},
        )
    ).status_code == 409
