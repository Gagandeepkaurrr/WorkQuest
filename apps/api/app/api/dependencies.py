from dataclasses import dataclass
from uuid import UUID
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import digest, equal, now
from app.db.sessions import get_db
from app.modules.auth.models import AuthSession, User


@dataclass
class Auth:
    user: User
    session: AuthSession

    @property
    def id(self) -> UUID:
        return self.user.id


async def authenticate(request: Request, db: AsyncSession, csrf: bool = True) -> Auth:
    token = request.cookies.get(get_settings().cookie_name, '')
    session = await db.scalar(select(AuthSession).where(AuthSession.token_digest == digest(token), AuthSession.revoked_at.is_(None), AuthSession.expires_at > now())) if token else None
    user = await db.get(User, session.user_id) if session else None
    if not session or not user or user.deleted_at or (user.demo_expires_at and user.demo_expires_at <= now()):
        raise AppError('UNAUTHENTICATED', 'Sign in to continue.', 401)
    if csrf and request.method not in ('GET','HEAD','OPTIONS') and not equal(request.headers.get('X-CSRF-Token',''), session.csrf_secret):
        raise AppError('FORBIDDEN', 'Refresh your session and try again.', 403)
    return Auth(user, session)


async def current_auth(request: Request, db: AsyncSession = Depends(get_db)) -> Auth:
    return await authenticate(request, db)


async def admin_auth(auth: Auth = Depends(current_auth)) -> Auth:
    if auth.user.role != 'admin' or auth.user.demo_expires_at:
        raise AppError('FORBIDDEN','Administrator access required.',403)
    return auth
