from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MediaTaskModel(BaseModel):
    """
    Model đại diện cho một bản ghi Task lưu trữ trong MongoDB.
    """
    id: str = Field(..., alias="_id") # task_id của Celery
    url: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    format: str
    quality: str
    status: str = "pending" # pending, processing, completed, failed
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "8fa447ce-a44f-4c26-8504-50a78f7302fa",
                "url": "https://youtube.com/watch?v=...",
                "title": "Video Title",
                "format": "mp3",
                "quality": "320k",
                "status": "completed",
                "file_name": "Video Title.mp3",
                "created_at": "2026-04-10T10:00:00Z"
            }
        }
