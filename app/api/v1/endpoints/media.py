import traceback
from fastapi import APIRouter, Depends, HTTPException
from app.services.media_service import MediaService
from app.schemas.media import MediaInfoResponse, MediaConvertRequest
from app.schemas.base import UnifiedResponse

router = APIRouter()

def get_media_service():
    return MediaService()

# API endpoint để lấy thông tin video từ URL
@router.get("/info", response_model=UnifiedResponse[MediaInfoResponse])
async def get_video_info(
    url: str,
    media_service: MediaService = Depends(get_media_service)
):
    """
    Lấy thông tin video từ URL (YouTube, v.v.)
    """
    try:
        info = await media_service.get_video_info(url)
        return UnifiedResponse(
            success=True,
            message="Lấy thông tin video thành công",
            data=info
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

# API endpoint để chuyển đổi video sang định dạng yêu cầu
@router.post("/convert", response_model=UnifiedResponse[dict])
async def convert_media(
    request: MediaConvertRequest,
    media_service: MediaService = Depends(get_media_service)
):
    """
    Tải và chuyển đổi video sang định dạng yêu cầu.
    """
    try:
        result = await media_service.process_media(
            url=request.url,
            target_format=request.format,
            quality_profile=request.quality
        )
        return UnifiedResponse(
            success=True,
            message="Chuyển đổi thành công",
            data=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý video: {str(e)}"
        )

        print("===========================")

        return UnifiedResponse(
            success=False,
            message=f"Lỗi lấy video: {repr(e)}",
            data=None
        )
