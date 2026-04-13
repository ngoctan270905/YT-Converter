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
    REDIS_URL: str
    
    # Static Files and Uploads
    STATIC_FILES_URL: str
    UPLOADS_DIR: str
    DOWNLOADS_DIR: str
    MAX_UPLOAD_SIZE_MB: int
    ALLOWED_IMAGE_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    # Multimedia Tools
    FFMPEG_PATH: str
    YT_DLP_PATH: str

    REDIS_BROKER_URL: str
    REDIS_BACKEND_URL: str



    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
