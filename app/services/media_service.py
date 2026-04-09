import json
import asyncio
import shutil
from pathlib import Path
from collections import defaultdict
from loguru import logger
from celery.result import AsyncResult

from app.core.config import settings
from app.schemas.media import MediaInfoResponse, VideoFormat, AudioFormat, MediaFormat
from app.tasks.media_tasks import download_video_task


class MediaService:
    """
    Service xử lý logic đa phương tiện (Phiên bản dùng Celery - Không DB).
    """

    def __init__(self):
        self.download_path = Path(settings.DOWNLOADS_DIR)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.yt_dlp_path = shutil.which(settings.YT_DLP_PATH) or settings.YT_DLP_PATH

    async def _execute_command(self, cmd: list[str]) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode().strip(), stderr.decode().strip()

    async def get_video_info(self, url: str) -> MediaInfoResponse:
        """Lấy thông tin video chi tiết (Dùng yt-dlp trực tiếp)."""
        cmd = [self.yt_dlp_path, "--quiet", "--no-warnings", "--print-json", "--skip-download", "--no-playlist", url]
        returncode, stdout, stderr = await self._execute_command(cmd)
        
        if returncode != 0:
            logger.error(f"YT-DLP Error: {stderr}")
            raise Exception(f"Lỗi lấy thông tin video: {stderr}")
        
        info = json.loads(stdout)
        
        # Logic lọc format tốt nhất
        best_formats = defaultdict(dict)
        for f in info.get("formats", []):
            height = f.get("height") 
            if not height or f.get("vcodec") == "none": continue 
            ext = f.get("ext")
            if ext not in ("mp4", "webm"): continue
            bitrate = f.get("tbr") or f.get("vbr") or 0
            key = (ext, height)
            if not best_formats.get(key) or bitrate > best_formats[key].get("bitrate", 0):
                best_formats[key] = {"format_id": f.get("format_id"), "quality": f"{height}p", "ext": ext, "bitrate": bitrate}
        
        video_formats = [VideoFormat(format_id=d["format_id"], quality=d["quality"], ext=d["ext"]) for k, d in best_formats.items() if d["ext"] == "mp4"]
        webm_formats = [VideoFormat(format_id=d["format_id"], quality=d["quality"], ext=d["ext"]) for k, d in best_formats.items() if d["ext"] == "webm"]
        video_formats.sort(key=lambda x: int(x.quality.replace("p", "")), reverse=True)
        webm_formats.sort(key=lambda x: int(x.quality.replace("p", "")), reverse=True)

        return MediaInfoResponse(
            title=info.get("title", "Unknown"),
            thumbnail=info.get("thumbnail"),
            duration=info.get("duration"),
            duration_text=self._format_duration(info.get("duration", 0)),
            author=info.get("uploader"),
            views=info.get("view_count"),
            upload_date=info.get("upload_date"),
            url=url,
            video_formats=video_formats,
            webm_formats=webm_formats,
            audio_formats=[AudioFormat(bitrate=128, ext="mp3"), AudioFormat(bitrate=192, ext="mp3"), AudioFormat(bitrate=320, ext="mp3")],
        )

    def start_convert_task(self, url: str, target_format: MediaFormat, quality_profile: str) -> str:
        """
        Đẩy task vào Celery và trả về task_id ngay lập tức.
        """
        # .delay() gửi task vào Redis
        task = download_video_task.delay(url, target_format.value, quality_profile)
        return task.id

    def get_task_status(self, task_id: str) -> dict:
        """
        Lấy trạng thái và kết quả task từ Celery Result Backend (Redis).
        """
        result = AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": result.status.lower(), # PENDING, STARTED, SUCCESS, FAILURE
            "result": None
        }
        
        if result.ready(): # Nếu đã hoàn thành (xong hoặc lỗi)
            if result.successful():
                response["result"] = result.result
            else:
                response["error"] = str(result.result)
                
        return response

    def _format_duration(self, seconds: int) -> str:
        m, s = divmod(seconds, 60); h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
