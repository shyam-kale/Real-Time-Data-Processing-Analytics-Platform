# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Build React frontend
# ═══════════════════════════════════════════════════════════════════════════════
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Python backend + serve frontend as static files
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS production

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Force SQLite — never connect to MySQL
ENV DATABASE_URL=sqlite+aiosqlite:///./dataflow.db
ENV DATABASE_URL_SYNC=sqlite:///./dataflow.db
ENV APP_ENV=production
ENV DEBUG=false

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend into backend static folder
COPY --from=frontend-builder /frontend/dist ./backend/static

WORKDIR /app/backend

# Initialize DB and seed demo user at build time
RUN python startup.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
