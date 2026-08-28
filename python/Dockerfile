# The api service and the jobs that feed it, which are the same image run two ways.
# Built from python/. See deploy/docker-compose.yml.

# Pinned by digest, so the same commit cannot rebuild on a different runtime and set of operating
# system packages later. The tag is left beside it to say what the digest is. Move both together.
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6 AS build

# Pinned to the version the lock file was written with, so a build is the same next month, and to
# the digest of that version, so the tag cannot be moved under it.
COPY --from=ghcr.io/astral-sh/uv:0.11.16@sha256:440fd6477af86a2f1b38080c539f1672cd22acb1b1a47e321dba5158ab08864d /uv /usr/local/bin/uv

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

FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

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
