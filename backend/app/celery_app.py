from celery import Celery
from celery.schedules import crontab
import os


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://mentions-graph-redis-master:6379/0",
)

celery = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)
celery.conf.task_routes = {"app.tasks.*": {"queue": "mentions"}}


celery.conf.beat_schedule = {
    "decrease-edges-daily": {
        "task": "app.tasks.decrease_old_edge_weights",
        # "schedule": crontab(hour=23, minute=59),  # run daily at 23:59
        "schedule": 30.0,
    },
}
celery.conf.timezone = "UTC"
