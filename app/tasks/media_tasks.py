import json
import subprocess
import shutil
from pathlib import Path
from loguru import logger
from app.core.celery_app import celery_app
from app.core.config import settings

@celery_app.task(name="download_video_task", bind=True, max_retries=2)
def download_video_task(self, url: str, target_format: str, quality_profile: str):
    """
    Task xử lý tải và chuyển đổi video ngầm (Phiên bản không dùng DB).
    """
    download_path = Path(settings.DOWNLOADS_DIR)
    download_path.mkdir(parents=True, exist_ok=True)
    
    # task_id của Celery dùng làm tên file UUID
    task_id = self.request.id
    
    yt_dlp_path = shutil.which(settings.YT_DLP_PATH) or settings.YT_DLP_PATH
    ffmpeg_path = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH

    try:
        # 1. Lấy thông tin video
        info_cmd = [yt_dlp_path, "--quiet", "--print-json", "--skip-download", url]
        info_res = subprocess.run(info_cmd, capture_output=True, text=True, encoding='utf-8')
        title = json.loads(info_res.stdout).get("title", "Unknown") if info_res.returncode == 0 else "Unknown"

        # 2. Thực hiện tải
        output_template = str(download_path / task_id) + ".%(ext)s"
        cmd = [yt_dlp_path, "--no-playlist", "--no-warnings", "-o", output_template]
        
        if target_format in ("mp3", "wav"):
            bitrate = quality_profile.lower().replace("k", "")
            cmd.extend(["-f", "bestaudio/best", "-x", "--audio-format", target_format, "--audio-quality", bitrate])
        else:
            height = quality_profile.lower().replace("p", "")
            cmd.extend(["-f", f"bestvideo[height<={height}]+bestaudio/best" if height.isdigit() else "best", "--merge-output-format", target_format])
        
        if ffmpeg_path:
            cmd.extend(["--ffmpeg-location", ffmpeg_path])
        
        cmd.append(url)

        logger.info(f"Worker bắt đầu tải: {url}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

        if result.returncode != 0:
            raise Exception(f"yt-dlp error: {result.stderr}")

        # 3. Tìm file thực tế
        actual_file = None
        for file in download_path.glob(f"{task_id}.*"):
            actual_file = file
            break
        
        if not actual_file:
            raise Exception("Không tìm thấy file sau khi tải xong.")

        # Trả về kết quả trực tiếp cho Celery Result Backend
        return {
            "status": "completed",
            "task_id": task_id,
            "file_name": f"{title}.{target_format}",
            "file_path": str(actual_file),
            "download_url": f"{settings.STATIC_FILES_URL}/downloads/{actual_file.name}"
        }

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise self.retry(exc=e, countdown=30)
