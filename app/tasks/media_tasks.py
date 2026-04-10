import json
import asyncio
import shutil
import time
import os
import re
import redis
from pathlib import Path
from collections import deque
from loguru import logger

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, get_database, close_mongo_connection
from app.repositories.media_repository import MediaRepository

# Regex lấy số % từ stdout của yt-dlp
PROGRESS_REGEX = re.compile(r'(\d{1,3}(?:\.\d+)?)%')

async def _run_command_async(
    cmd: list[str],
    task_id: str = None,
    realtime: bool = False,
    repo: MediaRepository = None,
    redis_client: redis.Redis = None
) -> tuple[int, str, str]:
    """
    Chạy lệnh shell bất đồng bộ, cập nhật progress vào Redis để tối ưu hiệu năng.
    """
    stderr_pipe = asyncio.subprocess.STDOUT if realtime else asyncio.subprocess.PIPE

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=stderr_pipe
    )

    # Tối ưu RAM: Chỉ giữ tối đa 30 dòng log cuối cùng
    stdout_logs = deque(maxlen=30)
    stderr_data = ""

    try:
        last_update_time = 0
        last_progress = -1
        phase = "video"

        if realtime:
            while True:
                line = await process.stdout.readline()
                if not line: break

                decoded_line = line.decode(errors="ignore").strip()
                if not decoded_line: continue

                stdout_logs.append(decoded_line)
                logger.debug(f"[{task_id}] {decoded_line}")

                # Detect Phase
                if "[download] Destination" in decoded_line or "has already been downloaded" in decoded_line:
                    if phase == "video" and last_progress >= 75:
                        phase = "audio"

                if "[Merger]" in decoded_line or "Merging formats into" in decoded_line:
                    phase = "merge"
                    if redis_client and task_id:
                        redis_client.set(f"task_progress:{task_id}", 95.0, ex=3600)

                # Detect progress %
                match = PROGRESS_REGEX.search(decoded_line)
                if match and task_id:
                    raw_progress = float(match.group(1))
                    if phase == "video": progress = raw_progress * 0.8
                    elif phase == "audio": progress = 80 + (raw_progress * 0.15)
                    elif phase == "merge": progress = 95.0
                    else: progress = raw_progress

                    progress = round(progress, 1)

                    # Update vào REDIS (Tối ưu Production)
                    if progress > last_progress and (time.time() - last_update_time >= 1):
                        if redis_client:
                            redis_client.set(f"task_progress:{task_id}", progress, ex=3600)
                        last_progress = progress
                        last_update_time = time.time()
        else:
            stdout_bytes, stderr_bytes = await process.communicate()
            stdout_logs.extend(stdout_bytes.decode(errors="ignore").splitlines())
            stderr_data = stderr_bytes.decode(errors="ignore") if stderr_bytes else ""

        await process.wait()

    except asyncio.CancelledError:
        logger.warning(f"[{task_id}] Task bị hủy. Đang kill subprocess...")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=3.0)
        except:
            process.kill()
        raise
    except Exception as e:
        logger.error(f"[{task_id}] Lỗi: {e}")
        if process.returncode is None: process.kill()
        raise
    finally:
        if process.returncode is None:
            try: process.kill()
            except: pass

    return (process.returncode, "\n".join(list(stdout_logs)), stderr_data)

@celery_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def download_video_task(self, url: str, target_format: str, quality_profile: str):
    """
    Task xử lý tải và chuyển đổi video (Sử dụng Redis cho Progress %).
    """
    task_id = self.request.id
    
    async def run_logic():
        await connect_to_mongo()
        db = get_database()
        repo = MediaRepository(db["media_tasks"])
        
        # Kết nối Redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        download_path = Path(settings.DOWNLOADS_DIR)
        download_path.mkdir(parents=True, exist_ok=True)

        yt_dlp_path = shutil.which(settings.YT_DLP_PATH) or settings.YT_DLP_PATH
        ffmpeg_path = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH

        try:
            # 1. Lấy thông tin sơ bộ
            info_cmd = [yt_dlp_path, "--quiet", "--no-warnings", "--print-json", "--skip-download", "--no-playlist", url]
            code, out, _ = await _run_command_async(info_cmd, task_id, realtime=False)
            
            if code != 0 or not out: raise Exception("Lỗi lấy thông tin video.")
            
            info_json = json.loads(out[out.find('{'):out.rfind('}')+1])
            title = info_json.get("title", "Unknown")
            
            await repo.update_task(task_id, {
                "title": title,
                "thumbnail": info_json.get("thumbnail"),
                "status": "processing"
            })
            r.set(f"task_progress:{task_id}", 0.0, ex=3600)

            # 2. Chuẩn bị lệnh tải
            output_template = str(download_path / task_id) + ".%(ext)s"
            cmd = [yt_dlp_path, "--no-playlist", "--newline", "--progress", "--no-color", "-o", output_template]

            if target_format in ("mp3", "wav"):
                bitrate = quality_profile.lower().replace("k", "")
                cmd.extend(["-f", "bestaudio/best", "-x", "--audio-format", target_format, "--audio-quality", bitrate])
            else:
                height = quality_profile.lower().replace("p", "")
                f_str = f"bestvideo[height<={height}]+bestaudio/best" if height.isdigit() else "best"
                cmd.extend(["-f", f_str, "--merge-output-format", target_format])

            if ffmpeg_path: cmd.extend(["--ffmpeg-location", ffmpeg_path])
            cmd.append(url)

            # 3. Chạy tải (realtime=True)
            code, out, err = await _run_command_async(cmd, task_id, realtime=True, redis_client=r)

            if code != 0: raise Exception(f"Lỗi khi tải video: {out[-500:]}")

            # 4. Tìm file kết quả
            actual_file = next(download_path.glob(f"{task_id}.*"), None)
            if not actual_file: raise Exception("Không tìm thấy file sau khi tải.")

            result = {
                "status": "completed",
                "task_id": task_id,
                "file_name": f"{title}.{target_format}",
                "file_path": str(actual_file),
                "download_url": f"{settings.STATIC_FILES_URL}/downloads/{actual_file.name}"
            }
            
            await repo.update_task(task_id, {
                "status": "completed",
                "progress": 100.0,
                "file_path": str(actual_file),
                "file_name": result["file_name"],
                "download_url": result["download_url"]
            })
            r.set(f"task_progress:{task_id}", 100.0, ex=3600)
            
            return result

        except Exception as e:
            await repo.update_task(task_id, {"status": "failed", "error_message": str(e)})
            r.delete(f"task_progress:{task_id}")
            logger.error(f"❌ Task failed: {str(e)}")
            raise self.retry(exc=e, countdown=10)
        finally:
            await close_mongo_connection()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: return loop.run_until_complete(run_logic())
    finally: loop.close()
