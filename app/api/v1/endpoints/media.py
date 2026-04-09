from fastapi import APIRouter, Depends, HTTPException
from app.services.media_service import MediaService
from app.schemas.media import MediaInfoResponse, MediaConvertRequest, MediaTaskResponse
from app.schemas.base import UnifiedResponse

router = APIRouter()

def get_media_service():
    return MediaService()

# 1. Lấy thông tin video
@router.get("/info", response_model=UnifiedResponse[MediaInfoResponse])
async def get_video_info(
    url: str,
    media_service: MediaService = Depends(get_media_service)
):
    try:
        info = await media_service.get_video_info(url)
        return UnifiedResponse(success=True, message="Lấy thông tin thành công", data=info)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 2. Khởi tạo task chuyển đổi (Async)
@router.post("/convert", response_model=UnifiedResponse[MediaTaskResponse])
async def convert_media(
    request: MediaConvertRequest,
    media_service: MediaService = Depends(get_media_service)
):
    try:
        task_id = media_service.start_convert_task(
            url=request.url,
            target_format=request.format,
            quality_profile=request.quality
        )
        return UnifiedResponse(
            success=True,
            message="Đã bắt đầu tiến trình chuyển đổi",
            data=MediaTaskResponse(task_id=task_id, status="pending")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Kiểm tra trạng thái Task
@router.get("/task/{task_id}", response_model=UnifiedResponse[dict])
async def get_task_status(
    task_id: str,
    media_service: MediaService = Depends(get_media_service)
):
    try:
        status = media_service.get_task_status(task_id)
        return UnifiedResponse(success=True, message="Trạng thái task", data=status)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
