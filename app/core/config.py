from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
        Lớp cấu hình trung tâm của ứng dụng.

        Lớp này kế thừa từ BaseSettings của Pydantic để tự động
        đọc cấu hình từ biến môi trường (environment variables)
        và file `.env`.
    """
    PROJECT_NAME: str
    API_V1_STR: str
    ENVIRONMENT: str
    
    # Logging Settings
    LOG_LEVEL: str
    LOG_FILE: str
    LOG_MAX_BYTES: int
    LOG_BACKUP_COUNT: int
    
    # MongoDB Settings
    MONGODB_URL: str
    DATABASE_NAME: str
    MIN_POOL_SIZE: int
    MAX_POOL_SIZE: int
    MONGODB_MAX_RETRIES: int
    MONGODB_RETRY_DELAY: int
    
    # Redis Settings (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Static Files and Uploads
    STATIC_FILES_URL: str = "http://localhost:8000/static"
    UPLOADS_DIR: str = "static/uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    # Multimedia Tools
    FFMPEG_PATH: str = "ffmpeg"
    YT_DLP_PATH: str = "yt-dlp"
    DOWNLOADS_DIR: str = "static/downloads"


    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
