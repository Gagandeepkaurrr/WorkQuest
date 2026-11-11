from fastapi import APIRouter, Depends
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import Auth, current_auth
from app.core.errors import AppError
from app.core.security import now, password_hasher
from app.db.sessions import get_db
from app.modules.auth.models import EmailJob, SecretPayload, User, UserPreferences
from app.modules.auth.schemas import DeleteInput, PreferencesInput, ProfileInput, UserView
from app.modules.auth.service import user_view
from app.modules.runs.models import CommandRequestRecord
from app.modules.runs.repository import lock_owner

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=UserView)
async def me(auth: Auth = Depends(current_auth)):
    return user_view(auth.user)


@router.patch("", response_model=UserView)
async def profile(
    body: ProfileInput, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    auth.user.display_name = body.display_name.strip() or "Learner"
    auth.user.updated_at = now()
    await db.commit()
    return user_view(auth.user)


@router.get("/preferences", response_model=PreferencesInput)
async def preferences(auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)):
    row = await db.get(UserPreferences, auth.id)
    return PreferencesInput.model_validate(row.value if row else {})


@router.patch("/preferences", response_model=PreferencesInput)
async def save_preferences(
    body: PreferencesInput, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.dialects.postgresql import insert

    await db.execute(
        insert(UserPreferences)
        .values(user_id=auth.id, value=body.model_dump())
        .on_conflict_do_update(index_elements=["user_id"], set_={"value": body.model_dump()})
    )
    await db.commit()
    return body


@router.delete("")
async def delete_account(
    body: DeleteInput, auth: Auth = Depends(current_auth), db: AsyncSession = Depends(get_db)
):
    if auth.user.demo_expires_at or not await run_in_threadpool(
        password_hasher.verify, body.password, auth.user.password_hash
    ):
        raise AppError("VALIDATION_ERROR", "Please enter your current password.")
    await lock_owner(db, auth.id)
    secret_ids = list(
        (
            await db.scalars(select(EmailJob.secret_payload_id).where(EmailJob.user_id == auth.id))
        ).all()
    ) + list(
        (
            await db.scalars(
                select(CommandRequestRecord.sensitive_response_payload_id).where(
                    CommandRequestRecord.user_id == auth.id
                )
            )
        ).all()
    )
    await db.execute(
        update(SecretPayload)
        .where(SecretPayload.id.in_([sid for sid in secret_ids if sid]))
        .values(encrypted_payload="", destroyed_at=now())
    )
    # Foreign-key cascades atomically remove owned resources. Workers must recheck ownership before publication.
    await db.execute(delete(User).where(User.id == auth.id))
    await db.commit()
    return {
        "message": "Account and owned data deleted. Backup retention is described in the data policy."
    }
