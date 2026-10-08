# syntax=docker/dockerfile:1

# ---- Stage 1: install dependencies into an isolated virtualenv ---------------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
# pip is only needed to build the venv; removing it means the runtime image ships no
# package installer (and none of pip's own CVEs, e.g. CVE-2025-8869).
RUN pip install -r requirements.txt && pip uninstall -y pip

# ---- Stage 2: slim runtime image ---------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="stockpilot-backend" \
      org.opencontainers.image.description="StockPilot inventory API (FastAPI)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Dedicated unprivileged user; numeric UID so Kubernetes can verify runAsNonRoot.
# The base image's own pip is removed too: nothing installs packages at runtime.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && python -m pip uninstall -y pip

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# Code stays root-owned and read-only for the app user.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Injected by CI (docker build --build-arg GIT_SHA=$GITHUB_SHA); shown by /api/info.
ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA}

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# prestart: wait for PostgreSQL -> alembic upgrade head -> optional demo seed.
# exec hands PID 1 to Uvicorn so SIGTERM from Docker/Kubernetes triggers a graceful shutdown.
CMD ["sh", "-c", "python -m app.prestart && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 20"]
