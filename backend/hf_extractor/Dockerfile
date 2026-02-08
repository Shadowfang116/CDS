FROM python:3.12-slim

# Install curl for healthcheck, tesseract-ocr and Urdu language data
RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    tesseract-ocr-urd \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build arguments for optional ML dependencies
ARG INSTALL_ML_DEPS=0
ARG INSTALL_VLM_DEPS=0

# Copy requirements and install base dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Conditionally install ML dependencies if requested
COPY requirements-ml.txt .
RUN if [ "$INSTALL_ML_DEPS" = "1" ]; then \
        pip install --no-cache-dir -r requirements-ml.txt && \
        echo "ML dependencies installed"; \
    else \
        echo "ML dependencies skipped (set INSTALL_ML_DEPS=1 to enable)"; \
    fi

# Conditionally install VLM dependencies if requested (for Qaari OCR)
COPY requirements-vlm.txt .
RUN if [ "$INSTALL_VLM_DEPS" = "1" ]; then \
        pip install --no-cache-dir -r requirements-vlm.txt && \
        echo "VLM dependencies installed"; \
    else \
        echo "VLM dependencies skipped (set INSTALL_VLM_DEPS=1 to enable)"; \
    fi

# Copy application code
COPY . .

EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]

