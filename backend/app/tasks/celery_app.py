"""
Celery 配置
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "rag_tasks",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.document_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,  # 10 min soft limit
    task_time_limit=900,       # 15 min hard limit
)
