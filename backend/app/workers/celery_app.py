import os
from celery import Celery

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_db = os.getenv("REDIS_DB", "0")

broker_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

celery_app = Celery(
    "bank_diligence_platform",
    broker=broker_url,
    backend=broker_url,
)


@celery_app.task(name="worker.ping")
def ping():
    return {"status": "ok"}

