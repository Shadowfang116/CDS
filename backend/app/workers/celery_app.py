import os
from celery import Celery
from celery.schedules import crontab

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_db = os.getenv("REDIS_DB", "0")

broker_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

celery_app = Celery(
    "bank_diligence_platform",
    broker=broker_url,
    backend=broker_url,
    include=["app.workers.tasks_ocr", "app.workers.tasks_digest", "app.workers.tasks_integrations", "app.workers.tasks_export", "app.workers.tasks_retention"],
)

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "run-due-digests-every-5-minutes": {
        "task": "digests.run_due_schedules",
        "schedule": 300.0,  # Every 5 minutes (300 seconds)
    },
    "process-integration-events-every-minute": {
        "task": "integrations.process_integration_events",
        "schedule": 60.0,  # Every 60 seconds
    },
    "retention-daily-2am-utc": {
        "task": "retention.run_retention_now",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 UTC
    },
}
celery_app.conf.timezone = "UTC"


@celery_app.task(name="worker.ping")
def ping():
    return {"status": "ok"}

