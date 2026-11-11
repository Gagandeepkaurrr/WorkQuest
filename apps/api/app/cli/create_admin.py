"""Explicit administrator bootstrap. No default credentials or HTTP promotion endpoint."""

import asyncio
import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from app.core.security import now, password_hasher
from app.db import models  # noqa: F401
from app.db.sessions import Session
from app.modules.auth.models import User


async def create(email, password, name):
    if not 12 <= len(password) <= 256:
        raise ValueError("Use a password of 12–256 characters.")
    async with Session.begin() as db:
        user = await db.scalar(select(User).where(User.normalized_email == email).with_for_update())
        if not user:
            user = User(
                normalized_email=email,
                password_hash=password_hasher.hash(password),
                display_name=name,
            )
            db.add(user)
        elif not password_hasher.verify(password, user.password_hash):
            raise ValueError("Existing-account promotion requires its current password.")
        if user.demo_expires_at:
            raise ValueError("Guests cannot be administrators.")
        user.role = "admin"
        user.email_verified_at = now()


if __name__ == "__main__":
    email = str(
        TypeAdapter(EmailStr).validate_python(input("Administrator email: ").strip().lower())
    )
    name = input("Display name: ").strip() or "Administrator"
    password = getpass.getpass("Password (or current password for promotion): ")
    asyncio.run(create(email, password, name))
    print("Administrator created/promoted. Sign in through the application.")
