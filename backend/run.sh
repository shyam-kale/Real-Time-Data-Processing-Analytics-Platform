#!/bin/sh
set -e

echo "🚀 Starting DataFlow..."

# Try to seed DB, but don't fail if it errors
echo "📦 Initializing database..."
python startup.py || echo "⚠️  DB init failed (non-fatal)"

# Start uvicorn - this MUST succeed
echo "🌐 Starting uvicorn on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
