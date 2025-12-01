# celery_app.py
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
# use redis result backend (simple)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

celery = Celery(
    "visora_celery",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# recommended: configure some defaults
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=int(os.getenv("TASK_TIME_LIMIT", 3600)),  # seconds per task hard limit
    task_soft_time_limit=int(os.getenv("TASK_SOFT_TIME_LIMIT", 3500)),
    worker_max_tasks_per_child=int(os.getenv("WORKER_MAX_TASKS_PER_CHILD", 50)),
)
