#!/usr/bin/env python3
"""Generate local-only configuration. Never overwrite existing configuration."""
from pathlib import Path
import secrets
import base64
root = Path(__file__).resolve().parent.parent
path = root / '.env'
if path.exists():
    print('Preserving existing .env')
else:
    password = secrets.token_urlsafe(24)
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    path.write_text(f'''APP_ENV=local
APP_ORIGIN=http://localhost:5173
POSTGRES_PASSWORD={password}
DATABASE_URL=postgresql+psycopg://workquest:{password}@localhost:55432/workquest
REDIS_URL=redis://localhost:56379/0
DELIVERY_PAYLOAD_ENCRYPTION_KEY={key}
DELIVERY_KEY_VERSION=1
SESSION_SECRET={secrets.token_urlsafe(48)}
METRICS_TOKEN={secrets.token_urlsafe(32)}
SMTP_HOST=localhost
SMTP_PORT=51025
SMTP_FROM=practice@workquest.local
AI_PROVIDER=local
DEMO_ENABLED=true
''')
    path.chmod(0o600)
    print('Created private local .env')
