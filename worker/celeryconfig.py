"""
Standalone Celery worker entry point.
Run from project root:
    celery -A worker.celeryconfig worker --loglevel=info
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.workers.celery_app import celery_app  # noqa: F401 – re-export
