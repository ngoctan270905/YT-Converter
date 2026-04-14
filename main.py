import sys
import asyncio
import subprocess
import time

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from slowapi.errors import RateLimitExceeded
from loguru import logger
from app.schemas.base import UnifiedResponse
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.middlewares.request_id import RequestIDMiddleware
from app.api.v1.router import api_router
from starlette.staticfiles import StaticFiles # New import
from pathlib import Path # New import
from app.core.redis_client import get_redis_client

# Configure logging before FastAPI app initialization
configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure uploads directory exists
    uploads_path = Path(settings.UPLOADS_DIR)
    uploads_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Đảm bảo thư mục uploads '{uploads_path}' tồn tại.")

    await connect_to_mongo()
    # warm up redis connection
    redis = get_redis_client()
    await redis.ping()
    logger.info("Khởi động ứng dụng thành công.")
    yield
    await close_mongo_connection()
    await redis.close()
    logger.info("Ứng dụng đã được tắt.")

# Khởi tạo ứng dụng FastAPI với metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FASTAPI Production Base Scaffold",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount static files (for avatars etc.)
app.mount(
    "/static",
    StaticFiles(directory=settings.UPLOADS_DIR.split('/')[0]), # Mount the 'static' directory
    name="static"
)


# ---- CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Exception Handlers (Override để đồng nhất format UnifiedResponse) ----

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    simplified_errors = [
        {
            "field": ".".join(map(str, err["loc"])),
            "message": err["msg"]
        }
        for err in exc.errors()
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=UnifiedResponse(
            success=False,
            message="Validation error",
            data=simplified_errors
        ).model_dump()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Xử lý các lỗi HTTP chung (404, 401, 403,...)."""
    return JSONResponse(
        status_code=exc.status_code,
        content=UnifiedResponse(
            success=False,
            message=str(exc.detail),
            data=None
        ).model_dump()
    )

# Setup SlowAPI Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ---- Middlewares ----
app.add_middleware(RequestIDMiddleware)

# ---- Routers ----
# Tích hợp toàn bộ API v1
app.include_router(api_router, prefix=settings.API_V1_STR)
