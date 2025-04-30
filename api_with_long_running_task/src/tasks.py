import time
from celery import Celery


celery_app = Celery(
    "worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)


@celery_app.task
def long_running_task():
    time.sleep(30)
    return "Task completed after 30 seconds"
