# The api service and the jobs that feed it, which are the same image run two ways.
# Built from python/. See deploy/docker-compose.yml.

FROM python:3.11-slim AS build

# Pinned to the version the lock file was written with, so a build is the same next month.
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /build

# The lock file alone first, so a code change does not reinstall PyTorch. --no-dev leaves out
# pytest, matplotlib and jupyter, none of which the server runs: training happens on the developer
# machine. On Linux the lock resolves the processor-only build of PyTorch, which is what makes this
# image hundreds of megabytes rather than gigabytes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY README.md ./
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.11-slim

# curl answers the health check in docker-compose.yml.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 nba

COPY --from=build /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    NBA_ML_DATA_DIR=/data \
    NBA_ML_BACKUP_DIR=/backups

USER nba
WORKDIR /home/nba

EXPOSE 8000

# One worker, because the prediction cap in nba_ml/api/limits.py counts per process and each
# prediction holds a few hundred megabytes. More workers means multiplying both.
CMD ["uvicorn", "nba_ml.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
