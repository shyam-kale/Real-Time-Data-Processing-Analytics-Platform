# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Build React frontend
# ═══════════════════════════════════════════════════════════════════════════════
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy package files and install deps
COPY frontend/package.json ./
RUN npm install

# Copy source and build
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

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend into backend static folder
COPY --from=frontend-builder /frontend/dist ./backend/static

# Set working directory to backend
WORKDIR /app/backend

# Create tables on startup (SQLite auto-creates the file)
RUN python create_tables.py || echo "Tables already exist"

EXPOSE 8000

# Start FastAPI — serves both API and frontend static files
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
