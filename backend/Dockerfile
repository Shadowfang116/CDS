FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    tesseract-ocr-urd \
    poppler-utils \
    fonts-dejavu-core \
    libreoffice-writer \
    libreoffice-core \
    default-jre-headless \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
# Install dependencies from pyproject.toml (includes cryptography and httpx)
# Use pip install with dependencies extracted from pyproject.toml
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
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

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
# Scripts are in parent directory, copy from there if needed
# For now, scripts will be mounted via docker-compose volume if needed

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

