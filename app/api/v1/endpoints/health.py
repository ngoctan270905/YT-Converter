from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase
from app.db.mongodb import get_database
from app.schemas.base import UnifiedResponse
from loguru import logger

router = APIRouter()

@router.get("/health", response_model=UnifiedResponse[dict])
async def health_check(db: AsyncDatabase = Depends(get_database)):
    """
    Kiểm tra trạng thái của ứng dụng và kết nối cơ sở dữ liệu.
    """
    db_status = "unhealthy"
    try:
        # Kiểm tra ping database
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Health check failed for database: {e}")
        
    return UnifiedResponse(
        success=(db_status == "healthy"),
        message=f"Application is running. Database is {db_status}.",
        data={
            "status": "online",
            "database": db_status
        }
    )
