from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue
from app.core.config import settings

celery_app = Celery("worker")

# ── Broker / Backend (tách riêng Redis DB) ──────────────────────────────
celery_app.conf.update(
    broker_url=settings.REDIS_BROKER_URL,           # redis://…/0
    result_backend=settings.REDIS_BACKEND_URL,        # redis://…/1

    # ── Serialization ──────────────────────────────────────────────────
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # ── Timezone ───────────────────────────────────────────────────────
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,

    # ── Result TTL ─────────────────────────────────────────────────────
    result_expires=3600,
    result_backend_transport_options={
        "retry_policy": {"timeout": 5.0},
    },

    # ── Broker resilience ──────────────────────────────────────────────
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_transport_options={
        "visibility_timeout": 7200,   # QUAN TRỌNG: > task_time_limit
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
    },

    # ── Worker tuning ──────────────────────────────────────────────────
    worker_concurrency=2,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,    # tránh memory leak
    worker_max_memory_per_child=500000, # 500MB hard limit

    # ── Task safety ────────────────────────────────────────────────────
    task_acks_late=True,
    task_reject_on_worker_lost=True,   # requeue nếu worker crash
    task_soft_time_limit=1500,         # 25 phút: raise SoftTimeLimitExceeded
    task_time_limit=1800,              # 30 phút: SIGKILL cứng

    # ── Queue routing ──────────────────────────────────────────────────
    task_default_queue="default",
    task_queues=(
        Queue("default",     Exchange("default"),     routing_key="default"),
        Queue("media",       Exchange("media"),       routing_key="media"),
        Queue("maintenance", Exchange("maintenance"), routing_key="maintenance"),
    ),
    task_routes={
        "app.tasks.media_tasks.*":       {"queue": "media"},
        "app.tasks.cleanup_tasks.*":     {"queue": "maintenance"},
    },

    # ── Beat schedule ──────────────────────────────────────────────────
    beat_schedule={
        "cleanup-old-files-every-hour": {
            "task": "app.tasks.cleanup_tasks.cleanup_old_files_task",
            "schedule": crontab(minute=0),
            "options": {
                "queue": "maintenance",
                "expires": 3600,          # bỏ qua nếu worker bận 1 giờ
            },
        },
    },
)

# Autodiscover (một nơi duy nhất, bỏ import trực tiếp ở trên)
celery_app.autodiscover_tasks(["app.tasks.media_tasks", "app.tasks.cleanup_tasks"])
