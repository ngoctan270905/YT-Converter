from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from app.schemas.base import UnifiedResponse

# Khởi tạo limiter với định danh mặc định là địa chỉ IP của client
limiter = Limiter(key_func=get_remote_address)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for RateLimitExceeded exception to return UnifiedResponse format.
    """
    response_data = UnifiedResponse[None](
        success=False,
        message="Too many requests. Please try again later.",
        data=None
    )
    return JSONResponse(
        status_code=429,
        content=response_data.model_dump()
    )
