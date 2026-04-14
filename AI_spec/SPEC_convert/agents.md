# Agents.md - SPEC_convert (Video/Audio Conversion Feature)

**Feature**: Cho phép users convert video YouTube sang MP3, MP4, WAV, WEBM với async processing  
**Current Status**: Existing & Production  
**Task**: Maintain, improve, hoặc extend functionality

---

## I. Thứ Tự Đọc File (Reading Order)

Đây là thứ tự AI agent **PHẢI** đọc file để hiểu toàn bộ feature:

### 1. `.github/AGENTS.md` (2 min)
- **Mục đích**: Hiểu kiến trúc tổng thể project
- **Lấy ra**: Architecture overview, key components, critical workflows

### 2. `AI_spec/AI_prompt_base.md` (10 min)
- **Mục đích**: Biết quy tắc viết code cho production
- **Lấy ra**: Async/Await, RORO, Security, Config, Testing, Deployment
- **Reference**: All development standards and patterns

### 3. `AI_spec/template_future_spec.md` (2 min - scan only)
- **Mục đích**: Hiểu structure của spec documentation
- **Lấy ra**: Spec format để reference khi cần document

### 4. `AI_spec/SPEC_convert/future_convert_spec.md` (15 min)
- **Mục đích**: Hiểu chi tiết feature convert
- **Lấy ra**: Requirements, architecture, data models, API endpoints, tasks, testing

### 5. `app/schemas/media.py` (10 min)
- **Mục đích**: Hiểu data validation & models
- **Lấy ra**: Validation logic, input/output models, security validation

### 6. `app/services/media_service.py` (15 min)
- **Mục đích**: Hiểu business logic & progress tracking
- **Lấy ra**: How to call external tools, track progress, handle async operations

### 7. `app/tasks/media_tasks.py` (5 min)
- **Mục đích**: Hiểu Celery task structure
- **Lấy ra**: Task pattern, retry strategy, error handling

### 8. `app/api/v1/endpoints/media.py` (10 min)
- **Mục đích**: Hiểu REST API interface
- **Lấy ra**: API design patterns, dependency injection, response handling

---

## II. Key Insights After Reading

Sau khi đọc xong 8 files trên, agent phải hiểu:

### Architecture Flow
```
Client Request
    ↓
[API Endpoint] (/convert, /info, /task/{id}, /download/{id})
    ↓
[Service Layer] (validation, task queuing, progress tracking)
    ↓
[Repository] (MongoDB operations)
    ↓
[Celery Task] (async download_video_task)
    ↓
[External Tools] (yt-dlp, ffmpeg)
    ↓
[Redis] (progress tracking, results)
    ↓
[Response to Client]
```

### Important Files & Their Role
| File | Role | Modify When |
|------|------|------------|
| `schemas/media.py` | Input validation | Add new formats/qualities |
| `services/media_service.py` | Business logic | Change conversion logic, progress |
| `tasks/media_tasks.py` | Task definition | Modify task retry/routing |
| `api/endpoints/media.py` | REST API | Add new endpoints |
| `repositories/media_repository.py` | DB operations | Add new queries |

---

## III. Common Tasks & How to Do Them

### Task A: Add New Output Format
1. Add to `MediaFormat` enum in `schemas/media.py`
2. Update validation in `MediaConvertRequest.validate_request()`
3. Update `_build_command()` in `media_service.py` to handle new format
4. Test with yt-dlp

**Files to modify**: `schemas/media.py`, `services/media_service.py`

### Task B: Improve Progress Tracking
1. Modify `PROGRESS_REGEX` or `_run_command_async()` phase detection
2. Adjust phase weighting (video:80%, audio:15%, merge:5%)
3. Test with real video downloads

**Files to modify**: `services/media_service.py`

### Task C: Fix Download Failure
1. Check error in `process_download()` error handler
2. Update MongoDB with error_message
3. Add retry logic in Celery task
4. Test with invalid URLs

**Files to modify**: `services/media_service.py`, `tasks/media_tasks.py`

### Task D: Add Rate Limiting
1. Add `@limiter.limit()` decorator in endpoints
2. Configure rate limit rules
3. Test with multiple concurrent requests

**Files to modify**: `api/endpoints/media.py`

---

## IV. Quick Reference

### URL Validation
```python
URL_REGEX = r'^https?://[a-zA-Z0-9\-\._~:/\?#\[\]@!\$&\'\(\)\*\+,;=%]+$'
```

### Supported Formats & Qualities
```python
# Video
MP4, WEBM → 2160p, 1440p, 1080p, 720p, 480p, 360p, 240p, 144p, best

# Audio
MP3, WAV → 320k, 192k, 128k, best
```

### Redis Keys
```python
task_progress:{task_id}  # Progress percentage (float)
```

### MongoDB Collection
```
media_tasks
  - _id: task_id (string)
  - url: YouTube URL
  - format: mp3/mp4/wav/webm
  - quality: user selected quality
  - status: pending → processing → completed/failed
  - file_path: path to output file
  - file_name: original title + format
  - progress: 0-100%
  - error_message: if failed
```

---

## V. Debugging Checklist

Nếu có issue với conversion:

- [ ] URL hợp lệ? (Check URL_REGEX)
- [ ] yt-dlp & ffmpeg cài chưa? (Check FFMPEG_PATH, YT_DLP_PATH in .env)
- [ ] Disk space đủ? (Check DOWNLOADS_DIR)
- [ ] Celery worker đang chạy? (Check queue)
- [ ] Redis connect được? (Check REDIS_URL)
- [ ] MongoDB connect được? (Check MONGODB_URL)
- [ ] Format + quality combo hợp lệ? (Check validate_request)
- [ ] Check logs (Loguru) cho error details

---

## VI. When to Contact Maintainer

- [ ] Need to change yt-dlp version (compatibility)
- [ ] Need to add new external tool (not just format)
- [ ] Need to scale to 1000+ concurrent tasks
- [ ] Need to integrate payment/auth
- [ ] Database schema change needed

---

## VII. Next Steps

**If implementing a task:**
1. Read files 1-8 in order above
2. Understand current implementation
3. Make changes following patterns
4. Write unit tests
5. Test locally with real videos
6. Commit with clear message

**If creating a new feature (e.g., Batch Convert):**
1. Read files 1-4 (project + spec template)
2. Create `SPEC_batch/agents.md` (like this file)
3. Write `SPEC_batch/future_batch_spec.md` using template
4. Reference existing convert implementation
5. Follow same patterns & conventions

---

**Note**: See `AI_spec/AI_prompt_base.md` for detailed development rules and patterns.
