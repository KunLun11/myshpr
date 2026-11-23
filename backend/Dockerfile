FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# dev
FROM base AS dev
RUN uv sync --frozen
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# prod
FROM base AS prod
# `s3` extra installs aioboto3: without it STORAGE_BACKEND=s3 fails at runtime.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra s3
COPY . .
EXPOSE 8000
# Call the venv binary directly so `uv run` never re-syncs dev dependencies.
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]