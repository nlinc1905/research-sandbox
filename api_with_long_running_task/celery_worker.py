# celery_worker.py
from src.tasks import celery_app

# This file is used to start the Celery worker:
# celery -A celery_worker worker --loglevel=info
