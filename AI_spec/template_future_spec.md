# Template cho Future Spec - [Tên Feature]

**Ngày tạo**: [YYYY-MM-DD]  
**Tác giả**: [Tên]  
**Status**: Draft | In Progress | Done  
**Priority**: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)

---

## I. Tổng Quan Feature

### 1. Mô Tả Ngắn
Mô tả 1-2 dòng về feature, lợi ích chính của nó.

**Ví dụ**: 
- Cho phép users batch convert multiple videos cùng lúc
- Lưu lịch sử convert để track và reuse

### 2. Lý Do Cần Làm
- Problem statement: Vấn đề hiện tại
- Impact: Tác động/lợi ích
- Business value: Giá trị cho người dùng/doanh nghiệp

---

## II. Requirements (Yêu Cầu Chi Tiết)

### 2.1 Functional Requirements (Chức Năng)

#### FR1: [Tên requirement]
- **Mô tả**: Chi tiết chức năng
- **Input**: Dữ liệu đầu vào (ví dụ: request body)
- **Process**: Quy trình xử lý
- **Output**: Dữ liệu đầu ra (ví dụ: response model)
- **Error cases**: Các tình huống lỗi có thể xảy ra

**Ví dụ FR1: Start Batch Convert**
- **Mô tả**: User có thể submit danh sách URLs để convert cùng lúc
- **Input**: 
  ```json
  {
    "batch_name": "My Playlist",
    "items": [
      {"url": "https://...", "format": "mp3", "quality": "320k"},
      {"url": "https://...", "format": "mp4", "quality": "720p"}
    ]
  }
  ```
- **Process**: 
  1. Validate mỗi URL
  2. Kiểm tra disk space có đủ không
  3. Tạo batch record trong DB
  4. Queue từng convert task vào Celery
- **Output**: 
  ```json
  {
    "batch_id": "uuid",
    "status": "queued",
    "total_items": 2,
    "queued_items": 2
  }
  ```
- **Error cases**: 
  - Invalid URL → 400
  - Disk full → 507
  - Too many items (>50) → 429

#### FR2: [Tên requirement]
- **Mô tả**: ...
- **Input**: ...
- **Process**: ...
- **Output**: ...
- **Error cases**: ...

### 2.2 Non-Functional Requirements

#### NFR1: Performance
- Batch limit: Max 50 items per request
- Response time: < 200ms để return batch_id
- Queue processing: Xử lý task từ queue trong 5 giây

#### NFR2: Availability & Reliability
- Task retry: Nếu convert fail, tự retry 2 lần với exponential backoff
- Timeout: Soft 25m, hard 30m per task
- Cleanup: Failed batches xóa sau 7 ngày

#### NFR3: Security
- Input validation: URL whitelist regex, format enum, quality enum
- Rate limiting: Max 10 batch requests per IP per minute
- File access: Chỉ user tạo batch mới có quyền download

#### NFR4: Scalability
- Concurrent batches: Support 100+ batches xử lý cùng lúc
- Database: Index batch_id, user_id, created_at
- Caching: Cache batch metadata 5 phút trong Redis

#### NFR5: Monitoring & Logging
- Log: Tất cả batch operations (create, progress, complete, fail)
- Metrics: Track conversion success rate, avg time per task
- Alerting: Alert nếu failure rate > 10% trong 1 giờ

---

## III. Architecture & Design

### 3.1 Data Model (Schema)

#### Batch Schema
```python
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class BatchItem(BaseModel):
    url: str = Field(..., description="Video URL")
    format: MediaFormat = Field(..., description="Target format")
    quality: str = Field(..., description="Quality profile")

class BatchCreateRequest(BaseModel):
    batch_name: str = Field(..., min_length=1, max_length=100)
    items: list[BatchItem] = Field(..., min_items=1, max_items=50)

class BatchResponse(BaseModel):
    batch_id: str
    batch_name: str
    status: str  # queued, processing, completed, failed, partial
    total_items: int
    completed_items: int
    failed_items: int
    created_at: datetime
    updated_at: datetime
    user_id: str | None = None

class BatchStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
```

#### Database Model
```
Collection: batches
{
  "_id": ObjectId,
  "batch_id": "uuid-string",
  "batch_name": "My Playlist",
  "user_id": "user-uuid",
  "status": "processing",
  "items": [
    {
      "task_id": "celery-task-id",
      "url": "https://...",
      "format": "mp3",
      "quality": "320k",
      "status": "processing",
      "progress": 45.5,
      "created_at": ISODate,
      "completed_at": null,
      "error": null,
      "file_path": null
    },
    ...
  ],
  "stats": {
    "total": 2,
    "queued": 0,
    "processing": 1,
    "completed": 1,
    "failed": 0
  },
  "created_at": ISODate,
  "updated_at": ISODate,
  "expires_at": ISODate  # TTL index 7 days
}
```

### 3.2 API Endpoints

#### POST /v1/media/batch/create
- Request: `BatchCreateRequest`
- Response: `UnifiedResponse[BatchResponse]`
- Status: 201 Created
- Errors: 400, 422, 429, 507

#### GET /v1/media/batch/{batch_id}
- Response: `UnifiedResponse[BatchResponse]`
- Status: 200 OK
- Errors: 404

#### GET /v1/media/batch/{batch_id}/items
- Response: `UnifiedResponse[list[BatchItemResponse]]`
- Pagination: ?page=1&limit=20
- Status: 200 OK

#### DELETE /v1/media/batch/{batch_id}
- Response: `UnifiedResponse[dict]`
- Status: 204 No Content
- Errors: 404, 403 (Unauthorized)

### 3.3 Celery Tasks

#### Task: process_batch_item
- Input: batch_id, item_index, url, format, quality
- Process: Download, convert, update batch status
- Output: file_path, file_size
- Retry: 2x với backoff 10s
- Queue: media

#### Task: cleanup_old_batches
- Schedule: Daily at 2 AM
- Process: Xóa batches > 7 ngày hoặc status=failed > 3 ngày
- Queue: maintenance

### 3.4 File Structure

```
app/
├── api/v1/
│   └── endpoints/
│       └── batch.py              # New: Batch endpoints
├── schemas/
│   └── batch.py                  # New: Batch models
├── services/
│   └── batch_service.py          # New: Batch business logic
├── repositories/
│   └── batch_repository.py       # New: Batch DB operations
├── tasks/
│   └── batch_tasks.py            # New: Batch Celery tasks
└── db/
    └── mongodb.py                # Update: Add batch collection index
```

---

## IV. Implementation Plan

### Phase 1: Database & Schema (Day 1)
- [ ] Tạo batch_repository.py
- [ ] Tạo batch.py schema
- [ ] Tạo MongoDB collection với indexes
- [ ] Unit test repository

### Phase 2: Service & Business Logic (Day 2)
- [ ] Tạo batch_service.py
- [ ] Implement create_batch, get_batch, list_batches
- [ ] Add validation & error handling
- [ ] Unit test service

### Phase 3: Celery Tasks (Day 2-3)
- [ ] Tạo batch_tasks.py
- [ ] Implement process_batch_item task
- [ ] Implement cleanup_old_batches scheduled task
- [ ] Test task retry logic

### Phase 4: API Endpoints (Day 3)
- [ ] Tạo batch.py endpoints
- [ ] Implement POST /batch/create
- [ ] Implement GET /batch/{id}
- [ ] Implement DELETE /batch/{id}
- [ ] Integration test endpoints

### Phase 5: Testing & Optimization (Day 4)
- [ ] Full integration tests
- [ ] Performance tests (load testing)
- [ ] Security tests (rate limit, auth)
- [ ] Deploy to staging

---

## V. Testing Strategy

### 5.1 Unit Tests
- **Repository**: Create, read, update batch records
- **Service**: Validation, business logic
- **Schemas**: Model validation

```python
# tests/unit/test_batch_service.py
@pytest.mark.asyncio
async def test_create_batch_success():
    service = BatchService(mock_repository)
    result = await service.create_batch(valid_request)
    assert result.batch_id is not None
    assert result.status == "queued"

@pytest.mark.asyncio
async def test_create_batch_too_many_items():
    service = BatchService(mock_repository)
    request = BatchCreateRequest(items=[...] * 51)  # 51 items
    with pytest.raises(ValueError):
        await service.create_batch(request)
```

### 5.2 Integration Tests
- Tạo batch → queue tasks → track progress → complete
- Error handling: Invalid URL, disk full, network error
- Cleanup: Old batches xóa sau TTL

```python
# tests/integration/test_batch_flow.py
@pytest.mark.asyncio
async def test_batch_convert_flow(client, mongo, redis, celery):
    # 1. Create batch
    response = await client.post("/v1/media/batch/create", json=batch_data)
    batch_id = response.json()["data"]["batch_id"]
    
    # 2. Verify batch queued
    response = await client.get(f"/v1/media/batch/{batch_id}")
    assert response.json()["data"]["status"] == "queued"
    
    # 3. Run Celery tasks
    celery.app.control.purge()  # Clear queue
    worker.apply_async(...)  # Execute tasks
    
    # 4. Check completion
    response = await client.get(f"/v1/media/batch/{batch_id}")
    assert response.json()["data"]["status"] == "completed"
```

### 5.3 Load Testing
- 100 batches x 10 items = 1000 concurrent tasks
- Verify: Memory usage, response time, no data loss

---

## VI. Deployment Checklist

- [ ] Code review passed
- [ ] Tests: 100% coverage trên new code
- [ ] Performance: Response time < 200ms
- [ ] Staging: Manual test toàn flow
- [ ] Monitoring: Alerts setup
- [ ] Documentation: API docs, runbook
- [ ] Rollback plan: Ready

---

## VII. Metrics & Monitoring

### Success Metrics
- Conversion success rate: > 95%
- Avg batch processing time: < 5 min cho 10 items
- User adoption: X% users dùng batch feature

### Monitoring Dashboard
- Batches created per day
- Conversion success/failure rate
- Avg items per batch
- Peak load (concurrent batches)

---

## VIII. Known Issues & Mitigation

| Issue | Severity | Mitigation |
|-------|----------|-----------|
| YouTube IP block khi batch lớn | High | Rate limit tasks, use proxy rotation |
| Disk space exhausted | High | Check space trước, cleanup aggressive |
| Database connection pool exhausted | Medium | Monitor connection, increase pool |
| Network timeout | Medium | Retry with exponential backoff |

---

## IX. Future Enhancements (Out of Scope)

- [ ] Batch scheduling (schedule for later)
- [ ] Email notifications khi batch complete
- [ ] Batch templates (save & reuse)
- [ ] Batch export (all files as zip)
- [ ] User quotas (max batches per day)

---

## X. References

- AGENTS.md: Project conventions
- AI_prompt_base.md: Development guidelines
- PRODUCTION_ISSUES.md: Known issues to address
- MongoDB schema: app/db/mongodb.py
- Existing batch-like code: app/services/media_service.py

