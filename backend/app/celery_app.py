from celery import Celery
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
