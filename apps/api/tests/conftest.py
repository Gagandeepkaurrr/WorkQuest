import os
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[3]
local = dotenv_values(root / '.env')
for k, v in local.items():
    if v is not None:
        os.environ.setdefault(k, v)
os.environ['APP_ENV'] = 'test'
os.environ['APP_ORIGIN'] = 'http://testserver'
os.environ['DATABASE_URL'] = os.environ['DATABASE_URL'].rsplit('/', 1)[0] + '/workquest_test'
os.environ['REDIS_NAMESPACE'] = 'workquest:test'

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from app.db.base import Base
from app.db.sessions import engine
from app.main import app

@pytest_asyncio.fixture(autouse=True)
async def clean_db(request):
    if '/integration/' not in str(request.fspath):
        yield
        return
    async with engine.begin() as conn:
        names = ', '.join('"'+t.name+'"' for t in Base.metadata.sorted_tables)
        if names:
            await conn.execute(text(f'TRUNCATE {names} RESTART IDENTITY CASCADE'))
    yield

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver', headers={'Origin':'http://testserver'}) as c:
        yield c
