# Future Convert Spec - Video/Audio Conversion Feature

**Ngày tạo**: 2026-04-14  
**Tác giả**: Team  
**Status**: Production (Existing)  
**Priority**: P1 (Core Feature)

---

## I. Tổng Quan Feature

### 1. Mô Tả Ngắn
Cho phép users chuyển đổi video YouTube sang các định dạng khác nhau (MP3, MP4, WAV, WEBM) với các mức chất lượng khác nhau, hỗ trợ theo dõi tiến độ real-time.

### 2. Lý Do Cần Làm
- **Problem**: Users muốn download video YouTube sang các format mà họ muốn
- **Impact**: Core feature của ứng dụng, giá trị lớn cho end-users
- **Business value**: Primary revenue/engagement driver

---

## II. Requirements (Yêu Cầu Chi Tiết)

### 2.1 Functional Requirements

#### FR1: Get Video Information
- **Mô tả**: Lấy thông tin chi tiết video từ YouTube trước khi convert
- **Input**: 
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }
  ```
- **Process**: 
  1. Validate URL với regex whitelist
  2. Gọi yt-dlp để lấy metadata (title, duration, formats, thumbnail)
  3. Parse formats, filter theo height/bitrate
  4. Sort formats by quality (MP4 first, then WEBM)
- **Output**: 
  ```json
  {
    "title": "Video Title",
    "thumbnail": "https://...",
    "duration": 240,
    "duration_text": "4:00",
    "author": "Channel Name",
    "views": 1000000,
    "upload_date": "20230101",
    "url": "https://...",
    "video_formats": [
      {"format_id": "18", "quality": "360p", "ext": "mp4"},
      {"format_id": "22", "quality": "720p", "ext": "mp4"}
    ],
    "audio_formats": [
      {"bitrate": 128, "ext": "mp3"},
      {"bitrate": 192, "ext": "mp3"},
      {"bitrate": 320, "ext": "mp3"}
    ]
  }
  ```
- **Error cases**: 
  - Invalid URL → 400
  - Video not found → 404
  - yt-dlp error → 500

#### FR2: Start Video Conversion
- **Mô tả**: Khởi tạo task chuyển đổi video
- **Input**: 
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "mp3",
    "quality": "320k"
  }
  ```
- **Process**: 
  1. Validate input (URL, format/quality enum, combo)
  2. Create task record in MongoDB (status: pending)
  3. Queue `download_video_task` vào Celery queue "media"
  4. Return task_id ngay (async)
- **Output**: 
  ```json
  {
    "task_id": "uuid-string",
    "status": "pending",
    "message": "Conversion started"
  }
  ```
- **Error cases**: 
  - Invalid URL → 400
  - Invalid format/quality combo → 422
  - Rate limit exceeded → 429
  - Disk full → 507

#### FR3: Get Conversion Status & Progress
- **Mô tả**: Theo dõi tiến độ conversion real-time
- **Input**: `task_id` (URL param)
- **Process**: 
  1. Check MongoDB for final status
  2. If processing: Get progress from Redis key `task_progress:{task_id}`
  3. Check Celery for task status
  4. Return combined status
- **Output**: 
  ```json
  {
    "task_id": "uuid",
    "status": "processing",
    "progress": 45.5,
    "error": null,
    "result": null
  }
  ```
  Hoặc khi completed:
  ```json
  {
    "task_id": "uuid",
    "status": "success",
    "progress": 100.0,
    "result": {
      "file_path": "/path/to/file.mp3",
      "file_name": "Title.mp3",
      "download_url": "https://api/download/uuid"
    },
    "error": null
  }
  ```
- **Error cases**: 
  - Task not found → 404

#### FR4: Download Converted File
- **Mô tả**: Tải file đã convert về máy
- **Input**: `task_id` (URL param)
- **Process**: 
  1. Check task status (must be completed)
  2. Verify file exists
  3. Return file with original filename
- **Output**: Binary file (MP3/MP4/WAV/WEBM)
- **Error cases**: 
  - Task not completed → 400
  - File not found → 404
  - Task not found → 404

### 2.2 Non-Functional Requirements

#### NFR1: Performance
- Response time: 
  - `/info`: < 5s (yt-dlp fetch)
  - `/convert`: < 200ms (return task_id immediately)
  - `/task/{id}`: < 100ms
- Conversion time: < 10 min cho most videos (với ffmpeg optimization)
- Progress updates: Cập nhật Redis mỗi 1 giây

#### NFR2: Availability & Reliability
- Uptime: 99.5% (ít nhất 95.04% trong 1 tháng)
- Task retry: Auto retry 2x với exponential backoff (10s, 20s)
- Timeout: Soft 25 min (raise exception), Hard 30 min (SIGKILL)
- Cleanup: Failed tasks xóa sau 7 ngày, successful tasks sau 30 ngày

#### NFR3: Security
- URL validation: Regex whitelist (no shell injection)
- Format/Quality: Enum-based (no command injection)
- File access: UUID filename (not user title)
- Rate limiting: 10 convert requests per IP per minute
- CORS: Only whitelist frontend URLs

#### NFR4: Scalability
- Concurrent conversions: Support 50+ tasks processing cùng lúc
- Celery concurrency: 2 workers (configurable)
- Memory per task: < 500MB
- Database: Indexes on task_id, status, created_at
- Caching: Progress cached 5 phút trong Redis

#### NFR5: Monitoring & Logging
- Logs: Tất cả operations (get_info, start_convert, progress, complete)
- Metrics: 
  - Conversion success rate (target > 95%)
  - Avg conversion time per format
  - Peak concurrent tasks
- Alerting: Alert nếu failure rate > 10% trong 1 giờ

---

## III. Architecture & Design

### 3.1 Data Model

#### MediaConvertRequest
```python
from pydantic import BaseModel, Field, model_validator
from enum import Enum

class MediaFormat(str, Enum):
    MP3 = "mp3"
    MP4 = "mp4"
    WAV = "wav"
    WEBM = "webm"

class AudioQuality(str, Enum):
    B128K = "128k"
    B192K = "192k"
    B320K = "320k"
    BEST = "best"

class VideoQuality(str, Enum):
    P2160 = "2160p"
    P1440 = "1440p"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"
    P360 = "360p"
    P240 = "240p"
    P144 = "144p"
    BEST = "best"

class MediaConvertRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    format: MediaFormat = Field(default=MediaFormat.MP3)
    quality: str = Field(default="best")
    
    @model_validator(mode="after")
    def validate_quality_format_combo(self) -> "MediaConvertRequest":
        if self.format in (MediaFormat.MP4, MediaFormat.WEBM):
            if self.quality not in [v.value for v in VideoQuality]:
                raise ValueError(f"Invalid video quality: {self.quality}")
        elif self.format in (MediaFormat.MP3, MediaFormat.WAV):
            if self.quality not in [a.value for a in AudioQuality]:
                raise ValueError(f"Invalid audio quality: {self.quality}")
        return self
```

#### MongoDB Collection: media_tasks
```
{
  "_id": "task_id_string",
  "url": "https://...",
  "format": "mp3",
  "quality": "320k",
  "status": "completed",  // pending, processing, completed, failed
  "title": "Video Title",
  "thumbnail": "https://...",
  "file_path": "/path/to/file.mp3",
  "file_name": "Title.mp3",
  "download_url": "https://api/static/downloads/uuid.mp3",
  "progress": 100.0,
  "error_message": null,
  "created_at": ISODate("2026-04-14T10:00:00Z"),
  "updated_at": ISODate("2026-04-14T10:05:00Z"),
  "expires_at": ISODate("2026-05-14T10:00:00Z")  // TTL: 30 days
}
```

### 3.2 API Endpoints

```
GET  /v1/media/info              → Get video info
POST /v1/media/convert           → Start conversion
GET  /v1/media/task/{task_id}    → Get status & progress
GET  /v1/media/download/{task_id}→ Download file
```

### 3.3 Celery Tasks

#### Task: download_video_task
- **Queue**: media
- **Retry**: 2x với backoff
- **Timeout**: Soft 25m, Hard 30m
- **Input**: url, target_format, quality_profile
- **Process**:
  1. Fetch video info với yt-dlp
  2. Build yt-dlp + ffmpeg command
  3. Execute command, stream stdout line-by-line
  4. Parse progress % từ output
  5. Update Redis key `task_progress:{task_id}`
  6. Find output file (uuid-based)
  7. Update MongoDB with result
- **Output**: file_path, file_size

#### Task: cleanup_old_files_task
- **Schedule**: Mỗi giờ (minute=0)
- **Queue**: maintenance
- **Process**: Xóa files > 30 ngày hoặc status=failed > 7 ngày
- **Output**: Số files xóa

### 3.4 Progress Tracking

**Regex**: `(\d{1,3}(?:\.\d+)?)%`  
**Phase-based weighting**:
- Video download: 80% của total progress
- Audio extraction/conversion: 15%
- Merge/Finalization: 5%

```python
if phase == "video":
    progress = raw * 0.8
elif phase == "audio":
    progress = 80 + raw * 0.15
else:
    progress = 95.0
```

**Redis Key**: `task_progress:{task_id}` (TTL: 7 days)

---

## IV. Implementation

### 4.1 Files & Structure
```
app/
├── api/v1/endpoints/
│   └── media.py                  # 4 endpoints
├── schemas/
│   └── media.py                  # Models
├── services/
│   └── media_service.py          # Business logic
├── repositories/
│   └── media_repository.py       # DB ops
├── tasks/
│   └── media_tasks.py            # Celery tasks
└── core/
    ├── celery_app.py             # Celery config
    └── redis_client.py           # Redis config
```

### 4.2 Key Files Touched
- `app/api/v1/endpoints/media.py`: REST endpoints
- `app/services/media_service.py`: Core conversion logic
- `app/tasks/media_tasks.py`: Celery task definition
- `app/schemas/media.py`: Validation models
- `app/repositories/media_repository.py`: MongoDB operations
- `.env`: FFMPEG_PATH, YT_DLP_PATH, DOWNLOADS_DIR

---

## V. Testing

### Unit Tests (30% coverage)
```
tests/unit/
├── test_media_schemas.py         # Validate URL, format/quality combos
├── test_media_service.py         # Business logic, progress parsing
└── test_media_repository.py      # DB CRUD operations
```

### Integration Tests (40% coverage)
```
tests/integration/
└── test_convert_flow.py
    - GET /info with valid URL
    - POST /convert, check task queued
    - GET /task/{id}, check progress
    - GET /download/{id}, download file
    - Error cases (invalid URL, format, etc)
```

### Load Testing (10% coverage)
```
locust -f tests/load/convert_load_test.py
- 50 concurrent users
- 100 total requests
- Measure: response time, success rate, memory
```

---

## VI. Deployment

### Prerequisites
- ffmpeg cài đặt (PATH hoặc .env)
- yt-dlp cài đặt (pip install yt-dlp)
- Redis running (Celery broker)
- MongoDB running (data storage)

### Startup
```bash
# Terminal 1: FastAPI server
uvicorn main:app --reload

# Terminal 2: Celery worker
celery -A app.core.celery_app worker -l info -Q default,media,maintenance --pool=solo

# Terminal 3: Celery beat (optional, for cleanup)
celery -A app.core.celery_app beat --loglevel=info
```

### .env Setup
```
FFMPEG_PATH=/usr/bin/ffmpeg
YT_DLP_PATH=yt-dlp
DOWNLOADS_DIR=./static/downloads/
REDIS_URL=redis://localhost:6379/0
MONGODB_URL=mongodb://localhost:27017
LOG_LEVEL=INFO
```

---

## VII. Known Issues & Mitigations

| Issue | Severity | Mitigation |
|-------|----------|-----------|
| YouTube IP block | High | Rate limit, Proxy rotation |
| Special chars in filename | Medium | Use UUID, not title |
| Disk space exhausted | High | Check space, cleanup aggressive |
| ffmpeg encoding error | Medium | Fallback to different codec |
| Network timeout | Low | Retry with backoff |

---

## VIII. Future Enhancements

- [ ] Support playlist conversion (batch)
- [ ] WebSocket real-time progress
- [ ] User account & history
- [ ] Payment/premium features
- [ ] Proxy support for YouTube block
- [ ] Video trimming/cropping
- [ ] Subtitle extraction

---

## IX. Metrics

**Current** (as of 2026-04-14):
- Conversion success rate: 92%
- Avg conversion time: 3-7 min (depends on video length)
- Daily active users: X
- Files stored: ~500GB

**Target**:
- Success rate: > 95%
- Avg time: < 5 min
- Support 100+ concurrent tasks

---

## X. References

1. AGENTS.md - Project conventions
2. AI_prompt_base.md - Development standards
3. app/services/media_service.py - Core logic
4. yt-dlp docs - https://github.com/yt-dlp/yt-dlp
5. ffmpeg docs - https://ffmpeg.org/documentation.html
6. Celery docs - https://docs.celeryproject.io/
