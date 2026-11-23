from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Identity


class User(Identity, Base):
    __tablename__ = "users"
    normalized_email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20), default="learner")
    email_verified_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]
    demo_expires_at: Mapped[datetime | None]
    updated_at: Mapped[datetime | None]


class AuthSession(Identity, Base):
    __tablename__ = "auth_sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_secret: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    last_seen_at: Mapped[datetime | None]
    user_agent: Mapped[str] = mapped_column(String(200), default="Browser")


class AuthToken(Identity, Base):
    __tablename__ = "auth_tokens"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(30))
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class SecretPayload(Identity, Base):
    __tablename__ = "secret_payloads"
    purpose: Mapped[str] = mapped_column(String(40))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    key_version: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime]
    destroyed_at: Mapped[datetime | None]


class EmailJob(Identity, Base):
    __tablename__ = "email_jobs"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    secret_payload_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("secret_payloads.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempt_count: Mapped[int] = mapped_column(default=0)
    lease_token: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None]
    last_dispatched_at: Mapped[datetime | None]
    updated_at: Mapped[datetime | None]


class Outbox(Identity, Base):
    __tablename__ = "outbox"
    topic: Mapped[str] = mapped_column(String(30))
    payload_id: Mapped[UUID]
    published_at: Mapped[datetime | None]
    attempts: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime | None]
