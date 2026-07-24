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
    # 本地无 Redis 时避免 delay()/连接长时间挂起拖垮 API 进程
    broker_connection_timeout=2,
    broker_connection_retry=False,
    broker_connection_retry_on_startup=False,
    redis_backend_health_check_interval=5,
    broker_transport_options={
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
        "retry_on_timeout": False,
    },
)
