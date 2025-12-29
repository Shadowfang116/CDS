FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn[standard] "pydantic[email]" pydantic-settings sqlalchemy psycopg[binary] alembic redis celery pyjwt python-multipart boto3 pypdf reportlab pytesseract pillow pdf2image pyyaml python-docx

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

