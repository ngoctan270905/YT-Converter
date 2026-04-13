import asyncio
from typing import Optional
from loguru import logger
from pymongo import AsyncMongoClient, uri_parser
from app.core.config import settings


class DatabaseManager:
    """
    Quản lý MongoDB client dùng chung cho toàn bộ ứng dụng.

    Thuộc tính:
        client: AsyncMongoClient hiện tại (None nếu chưa kết nối).
        db_name: Tên database được lấy từ cấu hình.
    """
    def __init__(self):
        self.client: Optional[AsyncMongoClient] = None
        self.db_name: str = settings.DATABASE_NAME


db_manager = DatabaseManager()


async def connect_to_mongo():
    """
    Kết nối tới MongoDB với cơ chế retry.

    - Khởi tạo AsyncMongoClient với cấu hình pool.
    - Thực hiện ping để kiểm tra server sẵn sàng.
    - Thử lại theo số lần cấu hình nếu thất bại.
    - Raise exception nếu vượt quá số lần retry.
    """
    attempt = 0
    while attempt < settings.MONGODB_MAX_RETRIES:
        try:
            attempt += 1
            client = AsyncMongoClient(
                settings.MONGODB_URL,
                minPoolSize=settings.MIN_POOL_SIZE,
                maxPoolSize=settings.MAX_POOL_SIZE,
                serverSelectionTimeoutMS=5000,
            )
            try:
                await client.admin.command("ping")
            except Exception:
                await client.close()  # tránh leak
                raise

            db_manager.client = client
            parsed = uri_parser.parse_uri(settings.MONGODB_URL)
            safe_url = f"{parsed['nodelist'][0][0]}:{parsed['nodelist'][0][1]}"
            logger.info(f"Đã kết nối MongoDB tại {safe_url} (Lần thử: {attempt})")
            return

        except Exception as e:
            if attempt >= settings.MONGODB_MAX_RETRIES:
                logger.error(f"Thất bại sau {attempt} lần thử: {e}")
                raise
            logger.warning(f"Lần thử {attempt} thất bại, thử lại sau {settings.MONGODB_RETRY_DELAY}s...")
            await asyncio.sleep(settings.MONGODB_RETRY_DELAY)


async def close_mongo_connection():
    """
    Đóng kết nối MongoDB và reset client về None.

    Thường được gọi khi ứng dụng shutdown.
    """
    if db_manager.client:
        await db_manager.client.close()
        db_manager.client = None  # reset về None sau khi close
        logger.info("Đã đóng kết nối MongoDB.")


def get_database():
    """
    Trả về đối tượng database hiện tại.

    Raise RuntimeError nếu chưa kết nối MongoDB.
    """
    if db_manager.client is None:
        raise RuntimeError("Database chưa kết nối")
    return db_manager.client[db_manager.db_name]

def get_database_from_client(client: AsyncMongoClient):
    """Dùng cho Celery task - lấy từ client được tạo trong task."""
    return client[db_manager.db_name]

def create_client() -> AsyncMongoClient:
    return AsyncMongoClient(
        settings.MONGODB_URL,
        minPoolSize=settings.MIN_POOL_SIZE,
        maxPoolSize=settings.MAX_POOL_SIZE,
        serverSelectionTimeoutMS=5000,
    )

def get_client():
    """
    Trả về MongoDB Async client hiện tại.

    Raise RuntimeError nếu chưa kết nối.
    """
    if db_manager.client is None:
        raise RuntimeError("Database chưa kết nối")
    return db_manager.client