#!/usr/bin/env python3
"""Migrate only the explicitly named disposable WorkQuest test database."""
import os
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parent.parent
for k,v in dotenv_values(root/'.env').items():
    if v is not None:
        os.environ.setdefault(k,v)
os.environ['DATABASE_URL']=os.environ['DATABASE_URL'].rsplit('/',1)[0]+'/workquest_test'
os.environ['APP_ENV']='test'
os.chdir(root/'apps/api')
from alembic.config import Config
from alembic import command
command.upgrade(Config('alembic.ini'),'head')
