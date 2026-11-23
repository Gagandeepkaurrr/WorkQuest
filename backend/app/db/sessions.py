from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()
kwargs = (
    {"poolclass": NullPool}
    if settings.app_env == "test"
    else {"pool_size": 10, "max_overflow": 10, "pool_timeout": 10}
)
engine = create_async_engine(settings.database_url.get_secret_value(), pool_pre_ping=True, **kwargs)
Session = async_sessionmaker(engine, expire_on_commit=False)
sync_engine = create_engine(
    settings.database_url.get_secret_value(), pool_pre_ping=True, pool_size=5, max_overflow=5
)
SyncSession = sessionmaker(sync_engine, expire_on_commit=False)


async def get_db():
    async with Session() as db:
        yield db
