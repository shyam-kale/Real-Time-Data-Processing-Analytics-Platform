# ─────────────────────────────────────────────────────────────
# Stage 1: Build React frontend
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy lockfiles first for better layer caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Accept backend URL at build time (Railway injects this)
ARG VITE_API_BASE_URL=/
ARG VITE_WS_BASE_URL=/
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL

RUN npm run build


# ─────────────────────────────────────────────────────────────
# Stage 2: Python backend + serve frontend static files
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend into backend/static so FastAPI serves it
COPY --from=frontend-builder /frontend/dist ./static

# Create uploads dir
RUN mkdir -p ./uploads

EXPOSE 8000

# Seed DB at runtime (not build time) so SQLite is always fresh on start
CMD ["sh", "-c", "python startup.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
