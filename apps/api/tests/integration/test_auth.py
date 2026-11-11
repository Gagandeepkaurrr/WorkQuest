from sqlalchemy import select

from app.core.security import decrypt_json, digest
from app.db.sessions import Session
from app.modules.auth.models import AuthToken, EmailJob, SecretPayload


async def email_token():
    async with Session() as db:
        job = (await db.scalars(select(EmailJob).order_by(EmailJob.created_at.desc()))).first()
        payload = await db.get(SecretPayload, job.secret_payload_id)
        return decrypt_json(payload.encrypted_payload)["token"]


async def register(client, email="learner@example.com"):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct horse battery staple", "display_name": "Alex"},
    )
    assert r.status_code == 202, r.text
    token = await email_token()
    r = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct horse battery staple"}
    )
    assert r.status_code == 200, r.text
    client.headers["X-CSRF-Token"] = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    return token


async def test_register_verify_login_csrf_logout(client):
    token = await register(client)
    assert (
        await client.post("/api/v1/auth/verify-email", json={"token": token})
    ).status_code == 400
    assert (await client.get("/api/v1/me")).json()["email_verified"] is True
    csrf = client.headers.pop("X-CSRF-Token")
    assert (await client.patch("/api/v1/me", json={"display_name": "No CSRF"})).status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    assert (await client.patch("/api/v1/me", json={"display_name": "New name"})).status_code == 200
    assert (await client.post("/api/v1/auth/logout")).status_code == 200
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_origin_reset_revokes_sessions_and_token_secrets(client):
    await register(client)
    assert (
        await client.post(
            "/api/v1/auth/forgot-password",
            headers={"Origin": "https://evil.example"},
            json={"email": "learner@example.com"},
        )
    ).status_code == 403
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "learner@example.com"})
    assert r.status_code == 202
    token = await email_token()
    async with Session() as db:
        assert (
            await db.scalar(select(AuthToken).where(AuthToken.token_digest == digest(token)))
        ) is not None
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "a different long password"},
    )
    assert r.status_code == 200, r.text
    assert (await client.get("/api/v1/me")).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "password": "a different long password"},
        )
    ).status_code == 400


async def test_session_revocation_and_account_deletion(client):
    await register(client)
    sessions = (await client.get("/api/v1/auth/sessions")).json()["items"]
    assert len(sessions) == 1 and "token_digest" not in sessions[0]
    assert (
        await client.request(
            "DELETE",
            "/api/v1/me",
            json={"password": "incorrect password", "confirmation": "DELETE"},
        )
    ).status_code == 400
    assert (
        await client.request(
            "DELETE",
            "/api/v1/me",
            json={"password": "correct horse battery staple", "confirmation": "DELETE"},
        )
    ).status_code == 200
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_password_reset_revokes_a_login_already_verifying_the_old_password(
    client, monkeypatch
):
    import asyncio

    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.modules.auth import router

    await register(client)
    await client.post("/api/v1/auth/forgot-password", json={"email": "learner@example.com"})
    token = await email_token()
    entered, release = asyncio.Event(), asyncio.Event()
    original = router.run_in_threadpool
    replacement_hash = router.password_hasher.hash("replacement long password")

    async def controlled(func, *args, **kwargs):
        if func == router.password_hasher.verify:
            entered.set()
            await release.wait()
        if func == router.password_hasher.hash:
            return replacement_hash
        return await original(func, *args, **kwargs)

    monkeypatch.setattr(router, "run_in_threadpool", controlled)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Origin": "http://testserver"},
    ) as concurrent:
        login = asyncio.create_task(
            concurrent.post(
                "/api/v1/auth/login",
                json={"email": "learner@example.com", "password": "correct horse battery staple"},
            )
        )
        await asyncio.wait_for(entered.wait(), 5)
        reset = asyncio.create_task(
            client.post(
                "/api/v1/auth/reset-password",
                json={"token": token, "password": "replacement long password"},
            )
        )
        await asyncio.wait({reset}, timeout=0.2)
        release.set()
        login_result, reset_result = await asyncio.wait_for(asyncio.gather(login, reset), 5)
        assert login_result.status_code == reset_result.status_code == 200
        assert (await concurrent.get("/api/v1/auth/session")).status_code == 401
