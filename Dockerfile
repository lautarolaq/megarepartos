# Megarepartos — single-container build para Cloud Run.
# El backend FastAPI sirve también el bundle estático del frontend.

# 1) Frontend build
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
# En prod, las requests a /api/* van al mismo origin que sirve el HTML.
ENV VITE_API_BASE_URL=
RUN npm run build

# 2) Backend deps
FROM python:3.12-slim AS backend-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/src /app/backend/src

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install /app/backend


# 3) Runtime: backend + frontend static
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    SERVE_FRONTEND=1 \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1000 app

COPY --from=backend-builder /opt/venv /opt/venv
COPY --chown=app:app backend /app/backend
COPY --from=frontend-builder --chown=app:app /app/frontend/dist /app/frontend/dist

USER app

EXPOSE 8080

# Cloud Run inyecta PORT (default 8080).
CMD ["sh", "-c", "uvicorn megarepartos.main:app --host 0.0.0.0 --port ${PORT:-8080} --app-dir /app/backend/src"]
