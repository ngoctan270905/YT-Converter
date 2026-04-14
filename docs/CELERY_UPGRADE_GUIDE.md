# Hướng dẫn Nâng cấp Cấu hình Celery (Sản xuất)

Tài liệu này hướng dẫn cách áp dụng cấu hình Celery mới để tối ưu hóa hiệu năng, tách biệt hàng đợi (Queues) và quản lý tài nguyên tốt hơn.

## 1. Các file cần thay đổi/tạo mới

| File | Hành động | Mục đích |
| :--- | :--- | :--- |
| `.env` & `.env.example` | Cập nhật | Thêm URL cho Broker và Backend riêng biệt. |
| `app/core/config.py` | Cập nhật | Khai báo các biến môi trường mới vào hệ thống. |
| `app/core/celery_app.py` | **Thay thế** | Áp dụng logic cấu hình mới của bạn. |
| `app/tasks/cleanup_tasks.py` | **Tạo mới** | Tách task dọn dẹp để khớp với Queue `maintenance`. |
| `app/tasks/media_tasks.py` | Cập nhật | Xóa task cũ và chuẩn hóa tên task để tự động Routing. |

---

## 2. Chi tiết thay đổi

### Bước 1: Cấu hình Môi trường (`.env`)
Thêm vào file `.env` (Sử dụng Database 0 cho Broker và Database 1 cho Result):
```env
REDIS_BROKER_URL=redis://localhost:6379/0
REDIS_BACKEND_URL=redis://localhost:6379/1
```

### Bước 2: Cập nhật `app/core/config.py`
Thêm vào class `Settings`:
```python
class Settings(BaseSettings):
    # ...
    REDIS_BROKER_URL: str
    REDIS_BACKEND_URL: str
```

### Bước 3: Tạo file `app/tasks/cleanup_tasks.py`
Di chuyển logic dọn dẹp từ `media_tasks.py` sang đây để hệ thống tự hiểu nó thuộc queue `maintenance`.
```python
from pathlib import Path
import time, os
from app.core.celery_app import celery_app
from app.core.config import settings
from loguru import logger

@celery_app.task
def cleanup_old_files_task():
    download_path = Path(settings.DOWNLOADS_DIR)
    if not download_path.exists(): return "Folder not found."
    now = time.time()
    deleted_count = 0
    for file in download_path.glob("*"):
        if file.is_file() and (now - os.path.getmtime(file) > 86400):
            try: os.remove(file); deleted_count += 1
            except: pass
    return f"Deleted {deleted_count} files."
```

### Bước 4: Chỉnh sửa `app/tasks/media_tasks.py`
- Xóa hàm `cleanup_old_files_task` cũ.
- Xóa tham số `name="..."` trong `@celery_app.task` của `download_video_task` để Celery tự động nhận diện theo path `app.tasks.media_tasks.download_video_task`.

---

## 3. Tác động và Lưu ý quan trọng

### Logic khác có bị ảnh hưởng không?
- **Có:** Nếu bạn đang gọi task bằng tên (ví dụ: `delay("cleanup_old_files_task")`), bạn phải đổi thành tên đầy đủ hoặc import function để gọi.
- **Có:** Bạn phải chạy Worker với lệnh mới để nó "nghe" tất cả các hàng đợi.

### Cách chạy Worker mới (Production)
Bạn cần chỉ định rõ các Queues đã khai báo:
```bash
celery -A app.core.celery_app worker -Q default,media,maintenance --loglevel=info
```

### Cách chạy Celery Beat (Lập lịch)
```bash
celery -A app.core.celery_app beat --loglevel=info
```

## 4. Kiểm tra (Validation)
Sau khi thay đổi, hãy chạy lệnh sau để kiểm tra cấu hình đã nhận đủ Queues chưa:
```bash
celery -A app.core.celery_app inspect active_queues
```
