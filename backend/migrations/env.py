from alembic import context
from app.db.base import Base
from app.db.sessions import sync_engine
from app.db import models  # noqa: F401

with sync_engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
