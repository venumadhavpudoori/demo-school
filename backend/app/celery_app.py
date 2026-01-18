"""Celery application configuration with Redis broker and result backend."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

# Create Celery application
celery_app = Celery(
    "school_erp",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.notifications", "app.tasks.reports", "app.tasks.imports"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Task routing (optional - for future scaling)
    task_routes={
        "app.tasks.notifications.*": {"queue": "notifications"},
        "app.tasks.reports.*": {"queue": "reports"},
        "app.tasks.imports.*": {"queue": "imports"},
    },
    
    # Task default queue
    task_default_queue="default",
    
    # Beat schedule (for periodic tasks)
    beat_schedule={},
)


def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app
