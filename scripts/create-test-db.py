from pathlib import Path
from dotenv import dotenv_values
import psycopg
root=Path(__file__).resolve().parent.parent
values=dotenv_values(root/'.env')
url=values['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://').rsplit('/',1)[0]+'/postgres'
with psycopg.connect(url,autocommit=True) as db:
    if not db.execute("SELECT 1 FROM pg_database WHERE datname='workquest_test'").fetchone():
        db.execute('CREATE DATABASE workquest_test')
print('Disposable workquest_test database available.')
