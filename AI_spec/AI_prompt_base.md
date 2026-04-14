# AI Prompt Base - YouTube Converter Backend Production

## I. Tổng Quan Dự Án

Đây là một backend xử lý chuyển đổi video YouTube sang các định dạng khác nhau (MP3, MP4, WAV, WEBM) một cách **production-ready** với khả năng:
- Xử lý hàng loạt yêu cầu đồng thời
- Theo dõi tiến độ real-time
- Tự động dọn dẹp tài nguyên
- Khôi phục khi gặp lỗi
- Logging chi tiết và monitoring

**Stack công nghệ:**
- FastAPI (async web framework)
- Celery + Redis (task queue & broker)
- MongoDB (persistent data storage)
- yt-dlp + ffmpeg (video processing)
- Loguru (structured logging)

---

## II. Quy Ước & Patterns Bắt Buộc

### A. Async/Await Pattern
- **LUÔN** sử dụng `async def` cho các function xử lý I/O
- Không bao giờ dùng `subprocess.run` (blocking) → dùng `asyncio.create_subprocess_exec`
- Tất cả database calls phải là async (pymongo async client)
- Không blocking calls trong event loop

**Ví dụ đúng:**
```python
async def get_video_info(url: str) -> dict:
    cmd = [str(self.yt_dlp_path), "--print-json", url]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return json.loads(stdout)
```

### B. RORO Pattern (Receive Object, Return Object)
- **Endpoints & Services**: Nhận Pydantic models cho input phức tạp, trả về objects
- **Repository**: Chấp nhận plain dict, Service chuyển đổi via `model.model_dump()`
- Simple inputs (id, flag) có thể truyền trực tiếp

**Ví dụ:**
```python
# Endpoint
@router.post("/convert", response_model=UnifiedResponse[MediaTaskResponse])
async def convert_media(request: MediaConvertRequest):
    # Service xử lý
    task_id = await media_service.start_convert_task(
        url=request.url,
        target_format=request.format,
        quality_profile=request.quality
    )
    return UnifiedResponse(success=True, data=MediaTaskResponse(task_id=task_id))

# Repository
async def create_task(self, data: dict):  # plain dict
    await self.collection.insert_one(data)
```

### C. Security First
- **URL Validation**: Luôn validate URL với regex whitelist trước xử lý
- **Format/Quality Enums**: Không bao giờ truyền user input trực tiếp vào shell commands → dùng enums
- **SQL/Command Injection Prevention**: yt-dlp commands phải được build với danh sách tĩnh, quality phải từ enum
- **Rate Limiting**: Áp dụng rate limit trên endpoints (đã setup với slowapi)

**Ví dụ:**
```python
from enum import Enum

class MediaFormat(str, Enum):
    MP3 = "mp3"
    MP4 = "mp4"
    WEBM = "webm"

class AudioQuality(str, Enum):
    B128K = "128k"
    B192K = "192k"
    B320K = "320k"

# Build command an toàn
if fmt in (MediaFormat.MP3, MediaFormat.WAV):
    cmd += ["-x", "--audio-format", fmt.value, "--audio-quality", quality]
```

---

## III. Quy Trình Phát Triển

### 1. Chuẩn Bị
- Clone repo, tạo venv, cài dependencies: `pip install -r requirements.txt`
- Tạo `.env` từ `.env.example` với các biến: `FFMPEG_PATH`, `YT_DLP_PATH`, `REDIS_URL`, `MONGODB_URL`
- Chắc chắn ffmpeg, yt-dlp được cài trên hệ thống

### 2. File Structure & Naming
- **Directories**: lowercase với underscores (e.g., `app/api/v1/endpoints/`)
- **Files**: lowercase với underscores (e.g., `media_service.py`)
- **Classes**: PascalCase (e.g., `MediaService`, `MediaRepository`)
- **Functions/Methods**: snake_case (e.g., `get_video_info`, `process_download`)
- **Constants**: UPPERCASE (e.g., `PROGRESS_REGEX`, `MAX_RETRIES`)

### 3. Schema & Validation
- Sử dụng Pydantic v2 với `model_validator` cho custom logic
- Luôn include type hints đầy đủ
- Thêm `description` cho fields phức tạp
- Validate input từ user ở schema level, không ở logic level

```python
from pydantic import BaseModel, Field, model_validator

class MediaConvertRequest(BaseModel):
    url: str = Field(..., description="Link video YouTube")
    format: MediaFormat = Field(default=MediaFormat.MP3)
    quality: str = Field(default="best")
    
    @model_validator(mode="after")
    def validate_quality_format_combo(self) -> "MediaConvertRequest":
        # Custom validation logic ở đây
        if self.format in (MediaFormat.MP4, MediaFormat.WEBM):
            if self.quality not in [v.value for v in VideoQuality]:
                raise ValueError(f"Quality '{self.quality}' không hợp lệ")
        return self
```

### 4. Service Layer
- Nhận Pydantic models, trả về dict/objects
- Điều phối giữa Repository, Tasks, External APIs
- Xử lý business logic phức tạp
- Quản lý progress tracking via Redis

```python
class MediaService:
    async def start_convert_task(self, url: str, target_format: str, quality: str) -> str:
        # 1. Validate input (nếu cần thêm)
        # 2. Gọi Celery task
        # 3. Lưu vào MongoDB via Repository
        # 4. Trả về task_id
        pass
```

### 5. Task Layer (Celery)
- Luôn dùng `@celery_app.task(bind=True)` để track task_id
- Set thích hợp: `max_retries`, `autoretry_for`, `retry_backoff`
- Route tasks vào queue phù hợp (media, maintenance, default)
- Handle exceptions, update progress, clear Redis keys

```python
@celery_app.task(bind=True, max_retries=2, autoretry_for=(Exception,), retry_backoff=True)
def download_video_task(self, url: str, target_format: str, quality: str):
    task_id = self.request.id
    try:
        # Chạy logic async
        return asyncio.run(process_download(task_id, url, target_format, quality))
    except Exception as e:
        # Retry với backoff
        raise self.retry(exc=e, countdown=10)
```

### 6. Progress Tracking
- Lưu progress vào Redis với key: `task_progress:{task_id}`
- Parse yt-dlp stdout real-time để cập nhật %
- Phase-based weighting: video (80%), audio (15%), merge (5%)
- Endpoint `/task/{task_id}` lấy progress từ Redis nếu task đang chạy

```python
PROGRESS_REGEX = re.compile(r'(\d{1,3}(?:\.\d+)?)%')

# Phase-based progress calculation
if phase == "video":
    progress = raw * 0.8
elif phase == "audio":
    progress = 80 + raw * 0.15
else:
    progress = 95.0

await redis_client.set(f"task_progress:{task_id}", progress)
```

### 7. Error Handling
- Luôn dùng `UnifiedResponse` model cho responses
- Log errors với Loguru, filter sensitive data
- HTTP exceptions có status codes đúng (400, 404, 500)
- Task exceptions tự retry với backoff

```python
# Unified response
from app.schemas.base import UnifiedResponse

return UnifiedResponse(
    success=False,
    message="Lỗi xử lý video",
    data=None
).model_dump()
```

## 8. Anti-Patterns (Strictly Forbidden)

- Không viết business logic trong FastAPI routes
- Không gọi blocking code trong async functions
- Không import chéo gây circular import

---

## IV. File Configuration & Paths

- **Config**: Tất cả biến cấu hình từ `.env` qua `settings` (Pydantic BaseSettings)
- **Paths**: Dùng `pathlib.Path`, không hardcode
- **Multiplatform**: Hỗ trợ Windows/Linux (không hardcode ổ đĩa)

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    FFMPEG_PATH: str
    YT_DLP_PATH: str
    DOWNLOADS_DIR: str
    REDIS_URL: str
    MONGODB_URL: str
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

# Sử dụng
download_path = Path(settings.DOWNLOADS_DIR)
download_path.mkdir(parents=True, exist_ok=True)
```

---

## V. Testing

### Unit Tests
- Dùng pytest + pytest-asyncio
- Mock external services (yt-dlp, ffmpeg, MongoDB, Redis)
- Test schemas, validators, business logic

### Integration Tests
- Test full flow: request → Celery task → MongoDB → response
- Setup test fixtures cho database, Redis
- Cleanup sau mỗi test

```bash
# Chạy tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

---

## VI. Deployment & Production

### Docker
- Dockerfile cho FastAPI server, Celery worker, Celery beat
- docker-compose.yml với FastAPI, Celery, Redis, MongoDB

### Environment Variables
- `.env.production` cho production
- Sensitive data: API keys, URLs, paths
- Khác nhau giữa dev/staging/production

### Monitoring & Health Checks
- `/health` endpoint đơn giản
- Log tất cả requests/responses (Loguru + middleware)
- Monitor Celery tasks, Redis, MongoDB connections
- Setup alerts cho errors

---

## VII. Performance & Scalability

### Concurrency
- Celery worker concurrency: 2 (tunable via env)
- Task timeout: soft 25m, hard 30m
- Prefetch multiplier: 1 (fair scheduling)

### Resource Management
- UUID filename (không video title)
- Auto-cleanup files sau 24h via maintenance task
- Semaphore để limit concurrent processing
- Memory limit per worker: 500MB

### Caching & Redis
- Redis DB 0: Celery broker
- Redis DB 1: Celery result backend
- Redis DB 2: Progress tracking

---

## VIII. Logging

- Sử dụng Loguru, format JSON cho production
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Filter sensitive data (URLs, credentials)
- Rotation policy: max 10MB, keep 5 files

```python
from loguru import logger

# Configure
from app.core.logging_config import configure_logging
configure_logging()

# Usage
logger.info("Task started", task_id=task_id)
logger.error("Download failed", error=str(e))
```

---

## IX. Tham Chiếu

1. **AGENTS.md**: Kiến trúc, components, examples
2. **PRODUCTION_ISSUES.md**: Danh sách 11 vấn đề cần fix theo priority
3. **Code files**:
   - `app/schemas/media.py`: Models & validation
   - `app/services/media_service.py`: Core logic
   - `app/tasks/media_tasks.py`: Celery tasks
   - `app/api/v1/endpoints/media.py`: REST endpoints
   - `app/repositories/media_repository.py`: MongoDB operations
   - `app/core/celery_app.py`: Celery configuration

---

## X. Checklist Trước Khi Commit

- [ ] Code async-first, không blocking calls
- [ ] Pydantic models với type hints đầy đủ
- [ ] Enum cho user inputs (security)
- [ ] UnifiedResponse cho tất cả responses
- [ ] Error handling & logging
- [ ] Unit tests viết
- [ ] No hardcoded paths/credentials
- [ ] .env variables sử dụng
- [ ] Docstrings/comments rõ ràng
- [ ] Tên variables/functions descriptive

---

**Bắt đầu**: Đọc AGENTS.md, sau đó vào SPEC_X folder tương ứng với feature cần làm.
