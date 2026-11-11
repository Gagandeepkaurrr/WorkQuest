"""Launch local API, web, durable dispatcher and local teammate worker. Ctrl-C stops children."""
from pathlib import Path
import subprocess
import signal
import time
root=Path(__file__).resolve().parent.parent
commands=[(['uv','run','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--no-access-log'],root/'apps/api'),(['pnpm','dev'],root),(['uv','run','celery','-A','app.jobs.celery_app:celery','worker','--pool=solo','--loglevel=WARNING','--without-gossip','--without-mingle'],root/'apps/api'),(['uv','run','python','-m','app.jobs.dispatcher'],root/'apps/api')]
children=[]
def stop(*_):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
try:
    for command,cwd in commands:children.append(subprocess.Popen(command,cwd=cwd))
    print('WorkQuest: http://localhost:5173 | Mailpit: http://localhost:8025',flush=True)
    while all(child.poll() is None for child in children):time.sleep(1)
except KeyboardInterrupt:pass
finally:
    for child in children:
        if child.poll() is None:child.terminate()
    for child in children:
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill()
