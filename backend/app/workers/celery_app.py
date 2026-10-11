import os

from celery import Celery

celery_app = Celery(
    "tradealert",
    broker=os.environ["CELERY_BROKER_URL"],
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_default_queue="notification_jobs",
    task_serializer="json",
    accept_content=["json"],
)