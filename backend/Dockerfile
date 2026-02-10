# Multi-stage production Dockerfile. Build with context = repo root:
#   docker build -f backend/Dockerfile .
# So that backend/ and docs/ are available.

# -----------------------------------------------------------------------------
# Stage 1: build dependencies (wheels/venv)
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install Python deps into a venv (no gunicorn in pyproject; we add it here)
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir virtualenv \
    && python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --no-cache-dir \
        fastapi \
        "uvicorn[standard]" \
        gunicorn \
        "pydantic[email]" \
        pydantic-settings \
        sqlalchemy \
        "psycopg[binary]" \
        alembic \
        redis \
        celery \
        pyjwt \
        python-multipart \
        boto3 \
        pypdf \
        reportlab \
        pytesseract \
        pillow \
        pdf2image \
        numpy \
        opencv-python-headless \
        pyyaml \
        python-docx \
        cryptography \
        httpx

# -----------------------------------------------------------------------------
# Stage 2: runtime (slim + system deps only, no dev caches)
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Runtime system deps (OCR, docs, JRE for some converters). Clean apt cache.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-urd \
    poppler-utils \
    fonts-dejavu-core \
    libreoffice-writer \
    libreoffice-core \
    default-jre-headless \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (Phase 7)
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --shell /bin/false --create-home appuser

WORKDIR /app

# Copy venv and app from builder / context
COPY --from=builder /opt/venv /opt/venv
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
# Docs (rulepack etc.) – required when not using bind mounts
COPY docs ./docs

# Optional: scripts if needed at runtime (e.g. rulepack tooling)
COPY scripts ./scripts
# Phase 9: migration runner (used by migrate service)
COPY backend/scripts /app/backend_scripts
RUN chmod +x /app/backend_scripts/run_migrations.sh

RUN chown -R appuser:appgroup /app /opt/venv
USER appuser

EXPOSE 8000

# Healthcheck: Python one-liner (no curl in final image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/deep'); exit(0 if r.status==200 else 1)" || exit 1

# Production: gunicorn + uvicorn workers
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "app.main:app"]
