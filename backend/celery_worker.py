#!/usr/bin/env python
"""
Celery worker entry point.

Usage:
    # Start worker with default settings
    celery -A celery_worker.celery worker --loglevel=info

    # Start worker with specific queues
    celery -A celery_worker.celery worker --loglevel=info -Q default,notifications,reports,imports

    # Start worker with concurrency setting
    celery -A celery_worker.celery worker --loglevel=info --concurrency=4

    # Start beat scheduler (for periodic tasks)
    celery -A celery_worker.celery beat --loglevel=info

    # Start both worker and beat together (development only)
    celery -A celery_worker.celery worker --beat --loglevel=info
"""

from app.celery_app import celery_app

# Export celery app for CLI usage
celery = celery_app

if __name__ == "__main__":
    celery.start()
