"""
Flower configuration for Celery task monitoring.

Usage:
    # Start Flower with this config
    celery -A celery_worker.celery flower --conf=flower_config.py

    # Or with command line options
    celery -A celery_worker.celery flower --port=5555 --broker=redis://localhost:6379/1
"""

from app.config import get_settings

settings = get_settings()

# Flower server settings
port = settings.flower_port
address = "0.0.0.0"

# Broker settings (uses same broker as Celery)
broker_api = settings.celery_broker_url

# Basic authentication (optional)
if settings.flower_basic_auth:
    basic_auth = [settings.flower_basic_auth]

# Persistent storage for task history
persistent = True
db = "flower.db"

# Task settings
max_tasks = 10000  # Maximum number of tasks to keep in memory

# Auto-refresh interval (in milliseconds)
auto_refresh = True

# Enable task time limit display
task_columns = "name,uuid,state,args,kwargs,result,received,started,runtime,worker"

# URL prefix (useful when running behind a reverse proxy)
url_prefix = ""

# Logging
logging = "INFO"
