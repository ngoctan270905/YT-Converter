import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.core.context import set_request_id, set_client_ip, set_user_agent

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware gắn Request-ID và lưu metadata của request vào ContextVar.

    Chức năng:
    - Tạo hoặc lấy `X-Request-ID` từ header.
    - Lưu request_id vào request.state và ContextVar.
    - Lấy IP client (hỗ trợ X-Forwarded-For khi qua proxy).
    - Lưu User-Agent của client.
    - Trả lại `X-Request-ID` trong response header.

    Middleware này giúp:
    - Theo dõi request trong hệ thống logging.
    - Phục vụ tracing và debug trong môi trường async.
    """
    async def dispatch(self, request: Request, call_next):
        # 1. Gắn Request-ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        set_request_id(request_id)
        
        # 2. Gắn IP Client (Hỗ trợ proxy bằng header X-Forwarded-For)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        set_client_ip(client_ip)
        
        # 3. Gắn User-Agent
        user_agent = request.headers.get("User-Agent", "unknown")
        set_user_agent(user_agent)
        
        response = await call_next(request)
        
        # Trả về request_id trong header
        response.headers["X-Request-ID"] = request_id
        return response
