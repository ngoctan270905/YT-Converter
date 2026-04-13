from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import os
import re
from app.db.mongodb import get_database
from app.repositories.media_repository import MediaRepository
from app.services.media_service import MediaService
from app.schemas.media import MediaInfoResponse, MediaConvertRequest, MediaTaskResponse, URL_REGEX
from app.schemas.base import UnifiedResponse

router = APIRouter()

def get_media_service():
    """
    Dependency Injection để khởi tạo Service và Repository.
    """
    db = get_database()
    collection = db["media_tasks"]
    repository = MediaRepository(collection)
    return MediaService(repository)


# 1. Lấy thông tin video
@router.get("/info", response_model=UnifiedResponse[MediaInfoResponse])
async def get_video_info(
    url: str,
    media_service: MediaService = Depends(get_media_service)
):
    try:
        # Kiểm tra URL Whitelist trước khi xử lý
        if not re.match(URL_REGEX, url):
            raise HTTPException(
                status_code=400, 
                detail="URL không hợp lệ."
            )
            
        info = await media_service.get_video_info(url)
        return UnifiedResponse(success=True, message="Lấy thông tin thành công", data=info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 2. Khởi tạo task chuyển đổi
@router.post("/convert", response_model=UnifiedResponse[MediaTaskResponse])
async def convert_media(
    request: MediaConvertRequest,
    media_service: MediaService = Depends(get_media_service)
):
    try:
        task_id = await media_service.start_convert_task( # Đẩy task vào Celery và lưu MongoDB
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
        status = await media_service.get_task_status(task_id)
        return UnifiedResponse(success=True, message="Trạng thái task", data=status)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# 5. Tải file kết quả
@router.get("/download/{task_id}")
async def download_file(
    task_id: str,
    media_service: MediaService = Depends(get_media_service)
):
    """
    Endpoint hỗ trợ tải file trực tiếp với tên file gốc.
    """
    try:
        status_info = await media_service.get_task_status(task_id)
        
        # Kiểm tra nếu task chưa xong hoặc không thành công
        if status_info.get("status") != "success" or not status_info.get("result"):
            raise HTTPException(
                status_code=400, 
                detail="Task chưa hoàn thành hoặc không tồn tại kết quả."
            )
            
        result = status_info["result"]
        file_path = result.get("file_path")
        file_name = result.get("file_name")

        # Kiểm tra file có tồn tại trên disk không
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Không tìm thấy file trên máy chủ.")

        # Trả về file với tên gốc
        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải file: {str(e)}")
