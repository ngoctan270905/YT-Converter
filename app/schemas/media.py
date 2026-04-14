from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Any
import re

class MediaFormat(str, Enum):
    MP3 = "mp3"
    MP4 = "mp4"
    WAV = "wav"
    WEBM = "webm"

class VideoQuality(str, Enum):
    P2160 = "2160p"
    P1440 = "1440p"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"
    P360 = "360p"
    P240 = "240p"
    P144 = "144p"
    BEST = "best"

class AudioQuality(str, Enum):
    B320K = "320k"
    B192K = "192k"
    B128K = "128k"
    BEST = "best"

class VideoFormat(BaseModel):
    format_id: str
    quality: str
    ext: str

class AudioFormat(BaseModel):
    bitrate: int | str
    ext: str


# Regex Whitelist cho URL: Cho phép các ký tự URL chuẩn, CHẶN dấu cách và ký tự shell nguy hiểm.
URL_REGEX = r'^https?://[a-zA-Z0-9\-\._~:/\?#\[\]@!\$&\'\(\)\*\+,;=%]+$'

class MediaConvertRequest(BaseModel):
    url: str = Field(..., description="Link video YouTube hoặc nền tảng khác")
    format: MediaFormat = Field(default=MediaFormat.MP3, description="Định dạng đích")
    quality: str = Field(default="best", description="Chất lượng (VD: 1080p cho video, 192k cho audio)")

    @model_validator(mode="after")
    def validate_request(self) -> "MediaConvertRequest":
        """
        Kiểm tra toàn diện tính hợp lệ của yêu cầu.
        """
        # 1. Kiểm tra URL an toàn
        if not re.match(URL_REGEX, self.url):
            raise ValueError(
                "URL không hợp lệ. Vui lòng thử lại."
            )

        # --- 2. Kiểm tra tương thích chất lượng ---
        fmt = self.format
        q = self.quality

        # Nếu là Video (MP4, WEBM)
        if fmt in (MediaFormat.MP4, MediaFormat.WEBM):
            if q not in [v.value for v in VideoQuality]:
                allowed = ", ".join([v.value for v in VideoQuality])
                raise ValueError(f"Chất lượng '{q}' không hợp lệ cho Video. Các giá trị cho phép: {allowed}")
        
        # Nếu là Audio (MP3, WAV)
        elif fmt in (MediaFormat.MP3, MediaFormat.WAV):
            if q not in [a.value for a in AudioQuality]:
                allowed = ", ".join([a.value for a in AudioQuality])
                raise ValueError(f"Chất lượng '{q}' không hợp lệ cho Audio. Các giá trị cho phép: {allowed}")
        
        return self

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
