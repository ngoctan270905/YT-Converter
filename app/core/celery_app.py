from celery import Celery
from app.core.config import settings

# Khởi tạo ứng dụng Celery
celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL  # Dùng chính Redis để lưu kết quả task
)

# Cấu hình Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    # Trên Windows, Celery thường gặp lỗi với pool mặc định (prefork)
    # Chúng ta sẽ xử lý việc này khi chạy lệnh khởi động worker.
)

# Tự động tìm kiếm các task trong thư mục tasks
celery_app.autodiscover_tasks(["app.tasks"])
