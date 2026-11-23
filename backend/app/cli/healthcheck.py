from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.core.config import get_settings

request = Request(
    "http://127.0.0.1:8000/health/ready",
    headers={"Host": urlsplit(get_settings().app_origin).netloc},
)
with urlopen(request, timeout=5) as response:
    if response.status != 200:
        raise SystemExit(1)
