# School ERP Backend

Multi-tenancy School ERP System Backend built with FastAPI, PostgreSQL, Redis, and Celery.

## Prerequisites

- Python 3.11+
- PostgreSQL
- Redis

## Installation

```bash
# Install dependencies using uv
uv sync

# Or with pip
pip install -e ".[dev]"
```

## Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings.

## Running the Application

### Start the API Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start Celery Worker

```bash
# Start worker with all queues
celery -A celery_worker.celery worker --loglevel=info -Q default,notifications,reports,imports

# Start worker with specific concurrency
celery -A celery_worker.celery worker --loglevel=info --concurrency=4
```

### Start Celery Beat (Periodic Tasks)

```bash
celery -A celery_worker.celery beat --loglevel=info
```

### Start Flower (Task Monitoring)

```bash
# With configuration file
celery -A celery_worker.celery flower --conf=flower_config.py

# Or with command line options
celery -A celery_worker.celery flower --port=5555 --broker=redis://localhost:6379/1

# With basic authentication
celery -A celery_worker.celery flower --port=5555 --basic_auth=admin:password
```

Access Flower dashboard at: http://localhost:5555

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run property-based tests only
pytest tests/properties/
```

## Project Structure

```
backend/
├── app/
│   ├── api/           # API endpoints
│   ├── middleware/    # Request middleware
│   ├── models/        # SQLAlchemy models
│   ├── repositories/  # Data access layer
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   ├── tasks/         # Celery background tasks
│   └── utils/         # Utility functions
├── alembic/           # Database migrations
├── tests/             # Test suite
├── celery_worker.py   # Celery worker entry point
├── flower_config.py   # Flower configuration
└── main.py            # FastAPI application entry point
```
