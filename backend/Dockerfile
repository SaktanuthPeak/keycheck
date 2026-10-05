# Multi-stage Dockerfile with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies
COPY pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# Copy application source
COPY . .

# Final sync with application
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 9000

CMD ["uvicorn", "apiapp.main:app", "--host", "0.0.0.0", "--port", "9000"]
