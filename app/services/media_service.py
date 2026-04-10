import json
import asyncio
import shutil
import redis
from pathlib import Path
from collections import defaultdict
from loguru import logger
from celery.result import AsyncResult

from app.core.config import settings
from app.schemas.media import MediaInfoResponse, VideoFormat, AudioFormat, MediaFormat
from app.tasks.media_tasks import download_video_task
from app.repositories.media_repository import MediaRepository


class MediaService:
    """
    Service xử lý logic đa phương tiện (Tích hợp Redis để lấy Progress nhanh).
    """

    def __init__(self, media_repository: MediaRepository):
        self._repository = media_repository
        self.download_path = Path(settings.DOWNLOADS_DIR)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.yt_dlp_path = shutil.which(settings.YT_DLP_PATH) or settings.YT_DLP_PATH
        # Kết nối Redis
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def _execute_command(self, cmd: list[str]) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode(errors='ignore').strip(), stderr.decode(errors='ignore').strip()

    async def get_video_info(self, url: str) -> MediaInfoResponse:
        """Lấy thông tin video chi tiết."""
        cmd = [self.yt_dlp_path, "--quiet", "--no-warnings", "--print-json", "--skip-download", "--no-playlist", url]
        returncode, stdout, stderr = await self._execute_command(cmd)
        
        if returncode != 0:
            logger.error(f"YT-DLP Error: {stderr}")
            raise Exception(f"Lỗi lấy thông tin video: {stderr[:200]}")
        
        info = json.loads(stdout)
        
        # Logic lọc format
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

    async def start_convert_task(self, url: str, target_format: MediaFormat, quality_profile: str) -> str:
        """
        Khởi tạo task, lưu vào MongoDB và đẩy vào Celery.
        """
        task = download_video_task.delay(url, target_format.value, quality_profile)
        task_id = task.id

        task_data = {
            "_id": task_id,
            "url": url,
            "format": target_format.value,
            "quality": quality_profile,
            "status": "pending"
        }
        await self._repository.create_task(task_data)
        return task_id

    async def get_task_status(self, task_id: str) -> dict:
        """
        Lấy trạng thái task. Lấy Progress từ Redis nếu đang chạy.
        """
        # 1. Kiểm tra MongoDB cho trạng thái cuối
        db_task = await self._repository.get_task_by_id(task_id)
        
        if db_task and db_task.get("status") in ("completed", "failed"):
            return {
                "task_id": task_id,
                "status": "success" if db_task["status"] == "completed" else "failed",
                "progress": 100.0 if db_task["status"] == "completed" else 0.0,
                "result": db_task if db_task["status"] == "completed" else None,
                "error": db_task.get("error_message")
            }

        # 2. Nếu đang chạy, lấy progress từ Redis
        redis_progress = self.redis.get(f"task_progress:{task_id}")
        progress = float(redis_progress) if redis_progress else 0.0

        # 3. Kiểm tra Celery cho trạng thái thực tế
        result = AsyncResult(task_id)
        status = result.status.lower()
        
        response = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "result": None
        }
        
        if result.ready():
            if result.successful():
                response["status"] = "success"
                response["progress"] = 100.0
                response["result"] = result.result
            else:
                response["status"] = "failed"
                response["error"] = str(result.result)
                
        return response

    async def get_history(self, limit: int = 20) -> list[dict]:
        return await self._repository.get_latest_tasks(limit)

    def _format_duration(self, seconds: int) -> str:
        m, s = divmod(seconds, 60); h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
