#!/bin/sh

echo "Starting DataFlow..."
echo "PORT=${PORT:-8000}"

# Seed DB - failures are non-fatal
python startup.py && echo "DB ready" || echo "DB init skipped"

# Start server - must use PORT from Railway env var
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
