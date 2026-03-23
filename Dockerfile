# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY README.md .
COPY alembic ./alembic
COPY alembic.ini .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends dumb-init tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin app

COPY --from=builder --chown=1000:1000 /app/.venv /app/.venv
COPY --from=builder --chown=1000:1000 /app/alembic /app/alembic
COPY --from=builder --chown=1000:1000 /app/alembic.ini /app/alembic.ini
COPY --chown=1000:1000 models /app/models

USER app

EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
