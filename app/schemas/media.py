from pydantic import BaseModel, Field

class VideoFormat(BaseModel):
    format_id: str
    quality: str
    ext: str

class AudioFormat(BaseModel):
    bitrate: int | str
    ext: str

class MediaConvertRequest(BaseModel):
    url: str = Field(..., description="Link video YouTube hoặc nền tảng khác")
    format: str = Field(default="mp3", description="Định dạng đích (mp3, mp4, wav)")
    quality: str = Field(default="best", description="Chất lượng (best, worst, 192k, 320k)")

class MediaInfoResponse(BaseModel):
    title: str
    thumbnail: str | None = None
    duration: int | None = None
    duration_text: str | None = None
    author: str | None = None
    views: int | None = None
    upload_date: str | None = None
    url: str
    video_formats: list[VideoFormat] = []
    webm_formats: list[VideoFormat] = []
    audio_formats: list[AudioFormat] = []

class MediaTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str | None = None
