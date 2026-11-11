FROM ghcr.io/astral-sh/uv:0.13.6 AS uv
FROM python:3.14.10-slim-trixie AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1
WORKDIR /app/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
FROM python:3.14.10-slim-trixie
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* && python -m pip uninstall -y pip && groupadd --gid 10001 workquest && useradd --uid 10001 --gid 10001 --create-home workquest
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/apps/api/.venv/bin:$PATH"
WORKDIR /app/apps/api
COPY --from=build /app/apps/api/.venv ./.venv
COPY --chown=10001:10001 apps/api/app ./app
COPY --chown=10001:10001 apps/api/content ./content
COPY --chown=10001:10001 apps/api/migrations ./migrations
COPY --chown=10001:10001 apps/api/alembic.ini ./
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
