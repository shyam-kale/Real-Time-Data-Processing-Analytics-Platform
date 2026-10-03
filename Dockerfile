# ─────────────────────────────────────────────────────────────
# Stage 1: Build React frontend
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --prefer-offline

COPY frontend/ ./

# Empty = same-origin, so all API calls are relative /api/v1/...
ARG VITE_API_BASE_URL=""
ARG VITE_WS_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL

RUN npm run build


# ─────────────────────────────────────────────────────────────
# Stage 2: Python backend + serve frontend static files
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend into static/ — FastAPI serves it at /
COPY --from=frontend-builder /frontend/dist ./static

# Create uploads dir
RUN mkdir -p ./uploads

# Health check so Railway knows when the app is ready
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

EXPOSE 8000

# startup.py seeds the DB; semicolon means uvicorn starts even if seeding fails
CMD ["sh", "-c", "python startup.py; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
