from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import digest

_SCRIPT = "local n=redis.call('INCR', KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n"


async def auth_rate_limit(request: Request):
    settings = get_settings()
    host = request.client.host if request.client else 'unknown'
    key = f'{settings.redis_namespace}:auth:{digest(host)}'
    try:
        async with Redis.from_url(settings.redis_url.get_secret_value(), socket_timeout=2) as redis:
            count = await redis.eval(_SCRIPT, 1, key, 60)
    except RedisError:
        raise AppError('DEPENDENCY_UNAVAILABLE', 'Sign-in is temporarily unavailable. Please retry.', 503) from None
    if count > (2000 if settings.app_env == 'test' else 30):
        raise AppError('RATE_LIMITED','Too many requests. Try again in one minute.',429)
