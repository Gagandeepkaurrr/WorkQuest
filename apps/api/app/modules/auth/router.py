from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import Auth, current_auth
from app.core.config import get_settings
from app.core.errors import AppError, unavailable
from app.core.rate_limits import auth_rate_limit
from app.core.security import DUMMY_HASH, now, password_hasher, random_token
from app.db.sessions import get_db
from app.modules.auth.models import AuthSession, AuthToken, User
from app.modules.auth.schemas import (
    Credentials,
    EmailInput,
    PasswordChange,
    Registration,
    ResetInput,
    TokenInput,
    UserView,
)
from app.modules.auth.service import new_session, queue_token, revoke_sessions, use_token, user_view

router = APIRouter(prefix="/auth", tags=["accounts"])
GENERIC = {"message": "If this address is eligible, an email will arrive shortly."}


@router.post("/register", status_code=202, dependencies=[Depends(auth_rate_limit)])
async def register(body: Registration, db: AsyncSession = Depends(get_db)):
    if not get_settings().public_signup_enabled:
        raise AppError("FORBIDDEN", "Registration is currently closed.", 403)
    email = str(body.email).strip().lower()
    # The unique email index is the final concurrency authority.
    from sqlalchemy.dialects.postgresql import insert

    hashed = await run_in_threadpool(password_hasher.hash, body.password)
    row = await db.scalar(
        insert(User)
        .values(
            normalized_email=email,
            password_hash=hashed,
            display_name=body.display_name.strip() or "Learner",
        )
        .on_conflict_do_nothing(index_elements=["normalized_email"])
        .returning(User.id)
    )
    if row:
        user = await db.get(User, row)
        assert user is not None  # Insert returned this primary key in the same transaction.
        await queue_token(db, user, "verify")
    await db.commit()
    return GENERIC


@router.post("/verify-email", dependencies=[Depends(auth_rate_limit)])
async def verify_email(body: TokenInput, db: AsyncSession = Depends(get_db)):
    user = await use_token(db, body.token, "verify")
    user.email_verified_at = now()
    await db.commit()
    return {"message": "Email verified. You can sign in."}


@router.post("/login", response_model=UserView, dependencies=[Depends(auth_rate_limit)])
async def login(
    body: Credentials, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    user = await db.scalar(
        select(User)
        .where(
            User.normalized_email == str(body.email).strip().lower(),
            User.deleted_at.is_(None),
            User.demo_expires_at.is_(None),
        )
        .with_for_update()
    )
    valid = await run_in_threadpool(
        password_hasher.verify, body.password, user.password_hash if user else DUMMY_HASH
    )
    if not user or not valid:
        raise AppError("UNAUTHENTICATED", "Email or password is incorrect.", 401)
    await new_session(db, user, request, response)
    await db.commit()
    return user_view(user)


@router.post("/logout")
async def logout(
    response: Response, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    auth.session.revoked_at = now()
    await db.commit()
    response.delete_cookie(
        get_settings().cookie_name,
        path="/",
        secure=get_settings().secure,
        httponly=True,
        samesite="lax",
    )
    return {"message": "Signed out."}


@router.get("/session", response_model=UserView)
async def session(auth: Auth = Depends(current_auth)):
    return user_view(auth.user)


@router.get("/csrf")
async def csrf(auth: Auth = Depends(current_auth)):
    return {"csrf_token": auth.session.csrf_secret}


@router.post("/forgot-password", status_code=202, dependencies=[Depends(auth_rate_limit)])
async def forgot(body: EmailInput, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(
        select(User).where(
            User.normalized_email == str(body.email).lower(),
            User.deleted_at.is_(None),
            User.demo_expires_at.is_(None),
        )
    )
    if user:
        await queue_token(db, user, "reset")
        await db.commit()
    return GENERIC


@router.post("/resend-verification", status_code=202, dependencies=[Depends(auth_rate_limit)])
async def resend(auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)):
    if not auth.user.email_verified_at and not auth.user.demo_expires_at:
        await queue_token(db, auth.user, "verify")
        await db.commit()
    return GENERIC


@router.post("/reset-password", dependencies=[Depends(auth_rate_limit)])
async def reset(body: ResetInput, db: AsyncSession = Depends(get_db)):
    user = await use_token(db, body.token, "reset")
    user.password_hash = await run_in_threadpool(password_hasher.hash, body.password)
    await revoke_sessions(db, user)
    await db.execute(
        update(AuthToken)
        .where(AuthToken.user_id == user.id, AuthToken.purpose == "reset")
        .values(used_at=now())
    )
    await db.commit()
    return {"message": "Password reset. Sign in with your new password."}


@router.post("/change-password")
async def change(
    body: PasswordChange,
    request: Request,
    response: Response,
    auth: Auth = Depends(current_auth),
    db: AsyncSession = Depends(get_db),
):
    # Serialize password changes with login, reset and deletion. Refresh the
    # identity-map values after waiting, then recheck the authenticated session.
    user = await db.scalar(
        select(User)
        .where(User.id == auth.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    await db.refresh(auth.session)
    if not user or user.deleted_at or auth.session.revoked_at or auth.session.expires_at <= now():
        raise AppError("UNAUTHENTICATED", "Sign in to continue.", 401)
    if not await run_in_threadpool(
        password_hasher.verify, body.current_password, auth.user.password_hash
    ):
        raise AppError("VALIDATION_ERROR", "The current password is incorrect.")
    auth.user.password_hash = await run_in_threadpool(password_hasher.hash, body.password)
    await revoke_sessions(db, auth.user)
    await new_session(db, auth.user, request, response)
    await db.commit()
    return {"message": "Password changed. Other sessions have been revoked."}


@router.get("/sessions")
async def sessions(auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)):
    records = (
        await db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == auth.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now(),
            )
            .order_by(AuthSession.created_at.desc())
            .limit(100)
        )
    ).all()
    return {
        "items": [
            {
                "id": s.id,
                "created_at": s.created_at,
                "expires_at": s.expires_at,
                "user_agent": s.user_agent,
                "current": s.id == auth.session.id,
            }
            for s in records
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke(
    session_id: UUID, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    record = await db.get(AuthSession, session_id)
    if not record or record.user_id != auth.id:
        raise unavailable()
    record.revoked_at = now()
    await db.commit()
    return {"message": "Session revoked."}


@router.post("/demo", response_model=UserView, dependencies=[Depends(auth_rate_limit)])
async def demo(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if not settings.demo_enabled or settings.secure:
        raise unavailable()
    user = User(
        normalized_email=f"{random_token()}@guest.invalid",
        password_hash=DUMMY_HASH,
        display_name="Demo learner",
        demo_expires_at=now() + timedelta(seconds=settings.demo_ttl_seconds),
    )
    db.add(user)
    await db.flush()
    await new_session(db, user, request, response)
    await db.commit()
    return user_view(user)
