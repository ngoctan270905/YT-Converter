# Sơ Đồ Luồng Chạy API Convert

## 🎯 Tổng Quan
API `/convert` xử lý việc chuyển đổi video YouTube thành MP3/MP4/WAV/WEBM với async processing qua Celery.

---

## 📋 Luồng Chi Tiết

### 1. Client Request → API Endpoint
```
POST /v1/media/convert
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "mp3",
  "quality": "320k"
}
```

**Endpoint**: `app/api/v1/endpoints/media.py::convert_media()`

**Input**: `MediaConvertRequest` (Pydantic model)
- url: str
- format: MediaFormat enum (mp3, mp4, wav, webm)
- quality: str (320k, 1080p, etc.)

**Validation**:
- URL regex whitelist
- Format/quality combo validation
- Model validation (required fields, types)

**Xử lý**:
- Inject `MediaService` via FastAPI dependency
- Call `await media_service.start_convert_task(request.url, request.format, request.quality)`
- Return `UnifiedResponse[MediaTaskResponse]`

**Output**:
```json
{
  "success": true,
  "message": "Đã bắt đầu tiến trình chuyển đổi",
  "data": {
    "task_id": "uuid-string",
    "status": "pending"
  }
}
```

---

### 2. Service Layer → Start Task
**Function**: `app/services/media_service.py::start_convert_task()`

**Input**:
- url: str
- target_format: MediaFormat
- quality_profile: str

**Xử lý**:
1. Import `download_video_task` từ `app.tasks.media_tasks`
2. Call `download_video_task.delay(url, target_format.value, quality_profile)`
   - `.delay()` tạo Celery task async, return `AsyncResult`
   - `task.id` = task_id (UUID)
3. Tạo `task_data` dict:
   ```python
   {
     "_id": task_id,
     "url": url,
     "format": target_format.value,  # "mp3"
     "quality": quality_profile,     # "320k"
     "status": "pending"
   }
   ```
4. Call `await self._repository.create_task(task_data)` → Lưu MongoDB

**Output**: `task_id` (str)

**Exception**: Nếu MongoDB lỗi → Exception

---

### 3. Celery Task → Async Processing
**Function**: `app/tasks/media_tasks.py::download_video_task()`

**Input** (từ Celery):
- url: str
- target_format: str ("mp3")
- quality_profile: str ("320k")

**Xử lý**:
1. `task_id = self.request.id` (Celery task ID)
2. Tạo async context:
   ```python
   async def run():
       client = create_client()  # MongoDB client
       try:
           db = get_database_from_client(client)
           repo = MediaRepository(db["media_tasks"])
           service = MediaService(repo)
           return await service.process_download(task_id, url, target_format, quality_profile)
       finally:
           await client.close()
   ```
3. Run async: `return asyncio.run(run())`

**Retry Logic**:
- `@celery_app.task(bind=True, max_retries=2, autoretry_for=(Exception,), retry_backoff=True)`
- Nếu fail → retry 2 lần với exponential backoff (10s, 20s)

**Output**: Dict từ `process_download()`

---

### 4. Service → Process Download
**Function**: `app/services/media_service.py::process_download()`

**Input**:
- task_id: str
- url: str
- target_format: str ("mp3")
- quality: str ("320k")

**Xử lý** (try/catch):

#### 4.1 Fetch Video Info
```python
info = await self._fetch_info(url, task_id)
# Returns: {"title": str, "thumbnail": str}
```

#### 4.2 Update Task Status
```python
await self._repository.update_task(task_id, {
    "title": info["title"],
    "thumbnail": info["thumbnail"],
    "status": "processing"
})
```

#### 4.3 Set Initial Progress
```python
await self.redis.set(f"task_progress:{task_id}", 0.0)
```

#### 4.4 Build yt-dlp Command
```python
cmd = self._build_command(url, target_format, quality, task_id)
# Returns: ["yt-dlp", "--no-playlist", "-x", "--audio-format", "mp3", "--audio-quality", "320", url]
```

#### 4.5 Execute Command with Progress Tracking
```python
code, out, err = await self._run_command_async(
    cmd, task_id, realtime=True, redis_client=self.redis
)
# Real-time: Parse stdout, update Redis progress every 1s
# Phase-based: video(80%) + audio(15%) + merge(5%)
```

#### 4.6 Check Result
```python
if code != 0:
    raise Exception(out[-300:])  # Last 300 chars of error
```

#### 4.7 Find Output File
```python
file = self._find_file(task_id)
# Glob: downloads/task_id.* → Path object
```

#### 4.8 Complete Task
```python
return await self._complete(task_id, file, info, target_format)
```

**Exception Handling**:
```python
except Exception as e:
    await self._repository.update_task(task_id, {
        "status": "failed",
        "error_message": str(e)
    })
    await self.redis.delete(f"task_progress:{task_id}")
    raise
```

---

### 5. Helper Functions

#### 5.1 _fetch_info()
**Input**: url, task_id
**Process**: yt-dlp --print-json (no download)
**Output**: {"title": str, "thumbnail": str}

#### 5.2 _build_command()
**Input**: url, fmt, quality, task_id
**Process**:
- Audio: ["-x", "--audio-format", fmt, "--audio-quality", bitrate]
- Video: ["-f", "bestvideo[height<=X]+bestaudio/best", "--merge-output-format", fmt]
**Output**: List[str] (yt-dlp command)

#### 5.3 _run_command_async()
**Input**: cmd, task_id, realtime=True, redis_client
**Process**:
- Create subprocess
- Read stdout line-by-line
- Parse progress with PROGRESS_REGEX
- Update Redis: `task_progress:{task_id}`
- Phase detection: video/audio/merge
**Output**: (returncode, stdout, stderr)

#### 5.4 _find_file()
**Input**: task_id
**Process**: `glob(f"{task_id}.*")`
**Output**: Path object

#### 5.5 _complete()
**Input**: task_id, file, info, fmt
**Process**:
- Create result dict with file info
- Update MongoDB: status=completed, progress=100, file_path, download_url
- Set Redis: progress=100
**Output**: Result dict

---

## 🔄 Client Polling Status

Sau khi nhận `task_id`, client có thể poll:

```
GET /v1/media/task/{task_id}
```

**Function**: `app/services/media_service.py::get_task_status()`

**Process**:
1. Check MongoDB: if completed/failed → return final status
2. Else: Get progress from Redis `task_progress:{task_id}`
3. Check Celery AsyncResult status
4. Return combined response

**Output**:
```json
{
  "task_id": "uuid",
  "status": "processing",  // pending/processing/success/failed
  "progress": 45.5,
  "result": null,          // or file info if completed
  "error": null            // or error message if failed
}
```

---

## 📁 File Structure Touched

```
app/
├── api/v1/endpoints/
│   └── media.py              # convert_media() endpoint
├── services/
│   └── media_service.py      # start_convert_task(), process_download()
├── tasks/
│   └── media_tasks.py        # download_video_task()
├── repositories/
│   └── media_repository.py   # create_task(), update_task()
└── core/
    ├── redis_client.py       # Progress tracking
    └── config.py             # Settings (paths, etc.)
```

---

## ⚡ Key Points

- **Async everywhere**: subprocess, DB calls, Redis
- **Progress tracking**: Real-time via Redis + stdout parsing
- **Error handling**: MongoDB status + Redis cleanup
- **Retry logic**: Celery auto-retry with backoff
- **File management**: UUID naming, auto-cleanup
- **Security**: URL validation, enum-based inputs

---

## 🎯 Flow Summary

```
Client POST /convert
    ↓
API Endpoint (validation)
    ↓
Service.start_convert_task() → MongoDB + Celery.delay()
    ↓
Celery Task (async context)
    ↓
Service.process_download()
    ├─ Fetch info
    ├─ Update status
    ├─ Build yt-dlp command
    ├─ Execute with progress tracking
    ├─ Find output file
    └─ Complete task
    ↓
Client polls /task/{id} for status
    ↓
Download file when completed
```
