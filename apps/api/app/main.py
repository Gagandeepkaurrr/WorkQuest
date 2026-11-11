import json
import secrets
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.contracts import ErrorEnvelope
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.observability import log
from app.core.security import equal
from app.db.sessions import Session
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router

settings = get_settings()
app = FastAPI(
    title="WorkQuest API",
    version="0.1.0",
    docs_url="/docs" if not settings.secure else None,
    redoc_url=None,
    responses={
        code: {"model": ErrorEnvelope} for code in [400, 401, 403, 404, 409, 413, 422, 429, 503]
    },
)
allowed_hosts = [(urlsplit(settings.app_origin).hostname or "localhost")]
if settings.backend_hostname:
    allowed_hosts.append(settings.backend_hostname)
if not settings.secure:
    allowed_hosts.extend(["localhost", "127.0.0.1"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

requests_count = Counter("wq_http_requests_total", "HTTP requests", ["method", "status"])
latency = Histogram("wq_http_request_seconds", "HTTP duration", ["method"])


def error_response(request: Request, code: str, message: str, status: int, details=None):
    return JSONResponse(
        {
            "error": {"code": code, "message": message, "details": details},
            "request_id": getattr(request.state, "request_id", "unavailable"),
        },
        status_code=status,
        headers={"Retry-After": "60"} if status == 429 else {},
    )


@app.middleware("http")
async def security_boundary(request: Request, call_next):
    request.state.request_id = secrets.token_hex(12)
    started = time.monotonic()
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer", "")
        if not origin and referer:
            parts = urlsplit(referer)
            origin = f"{parts.scheme}://{parts.netloc}"
        if origin != settings.app_origin.rstrip("/"):
            return error_response(
                request, "FORBIDDEN", "This request must come from WorkQuest.", 403
            )
        try:
            length = int(request.headers.get("content-length", "0") or 0)
        except ValueError:
            return error_response(request, "VALIDATION_ERROR", "Invalid content length.", 400)
        if length < 0 or length > 2 * 1024 * 1024:
            return error_response(request, "VALIDATION_ERROR", "Request is too large.", 413)
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 2 * 1024 * 1024:
                return error_response(request, "VALIDATION_ERROR", "Request is too large.", 413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
        if request._body:
            try:
                parsed = json.loads(request._body)
                pending = [(parsed, 0)]
                count = 0
                while pending:
                    value, depth = pending.pop()
                    count += 1
                    if depth > 30 or count > 20000:
                        raise ValueError("Structure limit")
                    if isinstance(value, dict):
                        pending.extend((v, depth + 1) for v in value.values())
                    elif isinstance(value, list):
                        pending.extend((v, depth + 1) for v in value)
            except ValueError, RecursionError, UnicodeError:
                return error_response(
                    request, "VALIDATION_ERROR", "Invalid or overly complex JSON.", 422
                )

    response = await call_next(request)
    response.headers.update(
        {
            "X-Request-ID": request.state.request_id,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
            "X-Frame-Options": "DENY",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }
    )
    if settings.secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    requests_count.labels(request.method, str(response.status_code)).inc()
    latency.labels(request.method).observe(time.monotonic() - started)
    log.info(
        "http_request",
        request_id=request.state.request_id,
        method=request.method,
        route=getattr(request.scope.get("route"), "path", "unmatched"),
        status=response.status_code,
        elapsed_ms=round((time.monotonic() - started) * 1000, 2),
    )
    return response


@app.exception_handler(AppError)
async def app_error(request: Request, exc: AppError):
    return error_response(request, exc.code, exc.message, exc.status, exc.details)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return error_response(
        request,
        "VALIDATION_ERROR",
        "Check the submitted fields.",
        422,
        [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()],
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    return error_response(
        request,
        "DEPENDENCY_UNAVAILABLE",
        "Your change was not acknowledged. Retry with the same request key.",
        503,
    )


@app.get("/health/live")
async def live():
    return {"status": "alive"}


@app.get("/health/ready")
async def ready():
    try:
        async with Session() as db:
            await db.execute(text("SELECT 1"))
        async with Redis.from_url(settings.redis_url.get_secret_value(), socket_timeout=2) as redis:
            await redis.ping()
    except Exception:
        raise AppError(
            "DEPENDENCY_UNAVAILABLE", "A required service is unavailable.", 503
        ) from None
    return {"status": "ready", "ai_provider": settings.ai_provider}


@app.get("/metrics", include_in_schema=False)
async def metrics(request: Request):
    if not settings.metrics_token.get_secret_value() or not equal(
        request.headers.get("authorization", ""),
        f"Bearer {settings.metrics_token.get_secret_value()}",
    ):
        raise AppError("NOT_FOUND", "Unavailable.", 404)
    from app.core.metrics import refresh_metrics

    await refresh_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

from app.db import models  # noqa: F401,E402
from app.modules.runs.router import router as runs_router  # noqa: E402
from app.modules.scenarios.router import router as scenarios_router  # noqa: E402

app.include_router(scenarios_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")

from app.modules.conversations.router import router as conversations_router  # noqa: E402

app.include_router(conversations_router, prefix="/api/v1")

from app.modules.checkpoints.router import router as checkpoints_router  # noqa: E402
from app.modules.reports.router import router as reports_router  # noqa: E402

app.include_router(checkpoints_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")

from app.modules.admin.router import router as admin_router  # noqa: E402

app.include_router(admin_router, prefix="/api/v1")
