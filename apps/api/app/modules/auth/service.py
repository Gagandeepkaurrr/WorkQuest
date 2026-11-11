from datetime import timedelta
from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import digest, encrypt_json, now, random_token
from app.modules.auth.models import AuthSession, AuthToken, EmailJob, Outbox, SecretPayload, User
from app.modules.auth.schemas import UserView


def user_view(user: User) -> UserView:
    return UserView(id=user.id, display_name=user.display_name, email=user.normalized_email if not user.demo_expires_at else '', role=user.role, email_verified=bool(user.email_verified_at), is_demo=bool(user.demo_expires_at), ai_provider='mock' if user.demo_expires_at else get_settings().ai_provider)


async def queue_token(db: AsyncSession, user: User, purpose: str):
    token = random_token()
    expiry = now() + (timedelta(hours=24) if purpose=='verify' else timedelta(minutes=30))
    db.add(AuthToken(user_id=user.id, purpose=purpose, token_digest=digest(token), expires_at=expiry))
    payload = SecretPayload(purpose='email', encrypted_payload=encrypt_json({'token':token,'email':user.normalized_email,'kind':purpose}), key_version=get_settings().delivery_key_version, expires_at=expiry)
    db.add(payload)
    await db.flush()
    job = EmailJob(user_id=user.id, kind=purpose, secret_payload_id=payload.id)
    db.add(job)
    await db.flush()
    db.add(Outbox(topic='email', payload_id=job.id))


async def use_token(db: AsyncSession, token: str, purpose: str) -> User:
    record = await db.scalar(select(AuthToken).where(AuthToken.token_digest==digest(token), AuthToken.purpose==purpose).with_for_update())
    if not record or record.used_at or record.expires_at <= now():
        raise AppError('VALIDATION_ERROR','This link is invalid or has expired.')
    user = await db.get(User, record.user_id)
    if not user or user.deleted_at:
        raise AppError('VALIDATION_ERROR','This link is invalid or has expired.')
    record.used_at = now()
    return user


async def revoke_sessions(db: AsyncSession, user: User):
    await db.execute(update(AuthSession).where(AuthSession.user_id==user.id).values(revoked_at=now()))


async def new_session(db: AsyncSession, user: User, request: Request, response: Response):
    settings = get_settings()
    old = request.cookies.get(settings.cookie_name)
    if old:
        await db.execute(update(AuthSession).where(AuthSession.token_digest==digest(old)).values(revoked_at=now()))
    raw = random_token()
    expiry = now() + timedelta(seconds=settings.session_max_age_seconds)
    if user.demo_expires_at:
        expiry = min(expiry, user.demo_expires_at)
    db.add(AuthSession(user_id=user.id, token_digest=digest(raw), csrf_secret=random_token(), expires_at=expiry, user_agent=request.headers.get('user-agent','Browser')[:200]))
    response.set_cookie(settings.cookie_name, raw, max_age=int((expiry-now()).total_seconds()), secure=settings.secure, httponly=True, samesite='lax', path='/')
