from celery import Celery
from celery.schedules import crontab  # noqa: F401
import os


BROKER_URL = os.getenv("BROKER_URL", "sentinel://sentinel-1:26379;sentinel-2:26379;sentinel-3:26379/0?master_name=mymaster")
BROKER_MASTER = os.getenv("BROKER_URL", "mymaster")

celery = Celery(
    "tasks",
    broker=BROKER_URL,
    backend=BROKER_URL,
    include=["app.tasks"],
)


celery.conf.update(
    broker_transport_options={
        "master_name": BROKER_MASTER,
        "sentinel_kwargs": {
            "password": None,
        },
    },
    result_backend_transport_options={
        "master_name": BROKER_MASTER,
        "sentinel_kwargs": {
            "password": None,
        },
        "visibility_timeout": 3600,  # 1 hour
    },
    task_routes={"app.tasks.*": {"queue": "mentions"}},
)


celery.conf.beat_schedule = {
    "decrease-edges-daily": {
        "task": "app.tasks.decrease_old_edge_weights",
        # "schedule": crontab(hour=23, minute=59),  # run daily at 23:59
        "schedule": 30.0,
    },
}
celery.conf.timezone = "UTC"
