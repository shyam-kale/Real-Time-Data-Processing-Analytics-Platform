#!/bin/sh
echo "PORT is: $PORT"
echo "Starting uvicorn..."
python startup.py || true
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
