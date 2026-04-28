# syntax=docker/dockerfile:1.7

# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: runtime ----------
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SERVE_FRONTEND=true \
    ENV=prod

# System deps for psycopg + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install backend deps first (better layer caching)
COPY backend/pyproject.toml backend/README.md* ./backend/
RUN pip install --upgrade pip && \
    pip install "fastapi>=0.110" "uvicorn[standard]>=0.27" "sqlalchemy>=2.0" \
                "pydantic>=2" "pydantic-settings>=2.0" "python-multipart>=0.0.9" \
                "pypdf>=4.2" "pdfplumber>=0.11" \
                "psycopg[binary]>=3.1" "alembic>=1.13" \
                "azure-ai-documentintelligence>=1.0.0" \
                "azure-storage-blob>=12.19" "azure-identity>=1.15"

# Copy backend source + the built frontend
COPY backend/ ./backend/
COPY --from=frontend /web/dist ./frontend/dist

# Make the backend importable
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# Run migrations then start the app. Use sh -c so DATABASE_URL is expanded at runtime.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
