import json
import asyncio
import shutil
import time
import re
from collections import deque
from pathlib import Path
from collections import defaultdict
from loguru import logger
from app.core.redis_client import get_redis_client, get_sync_redis_client
from celery.result import AsyncResult
from app.core.config import settings
from app.schemas.media import MediaInfoResponse, VideoFormat, AudioFormat, MediaFormat
from app.repositories.media_repository import MediaRepository

PROGRESS_REGEX = re.compile(r'(\d{1,3}(?:\.\d+)?)%')


class MediaService:
    """
    Service xử lý logic đa phương tiện (Tích hợp Redis để lấy Progress nhanh).
    """

    def __init__(self, media_repository: MediaRepository):
        """
        Khởi tạo MediaService với repository.

        Args:
            media_repository: Instance của MediaRepository để thao tác DB
        """
        self._repository = media_repository
        self.download_path = Path(settings.DOWNLOADS_DIR)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.yt_dlp_path = shutil.which(settings.YT_DLP_PATH) or settings.YT_DLP_PATH
        self.redis = get_redis_client()
        self.redis_sync = get_sync_redis_client()  # Sync client for Celery


    @staticmethod
    async def _execute_command(cmd: list[str]) -> tuple[int, str, str]:
        """Thực thi lệnh bất đồng bộ và trả về (returncode, stdout, stderr)."""

        # Tạo 1 tiến trình con subprocess để chạy lệnh yt-dlp
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        code = process.returncode
        if code is None:
            code = -1

        return (
            code,  # Lệnh có chạy thành công hay không ( 0 = OK, khác 0 = lỗi)
            stdout.decode(errors="ignore").strip(),  # Output chính
            stderr.decode(
                errors="ignore"
            ).strip(),  # Thông tin lỗi nếu có (nếu returncode khác 0)
        )


    async def get_video_info(self, url: str) -> MediaInfoResponse:
        """
        Lấy thông tin chi tiết video từ YouTube.

        Args:
            url: URL của video YouTube

        Returns:
            MediaInfoResponse: Thông tin video bao gồm title, formats, duration, etc.

        Raises:
            Exception: Nếu yt-dlp gặp lỗi khi lấy thông tin
        """

        # Sử dụng yt-dlp để lấy thông tin video dưới dạng JSON
        cmd: list[str] = [
            str(self.yt_dlp_path),
            "--quiet",
            "--no-warnings",
            "--print-json",
            "--skip-download",
            "--no-playlist",
            str(url),
        ]
        returncode, stdout, stderr = await self._execute_command(cmd)

        if returncode != 0:
            logger.error(f"YT-DLP Error: {stderr}")
            raise Exception(f"Lỗi lấy thông tin video: {stderr[:200]}")

        info = json.loads(stdout)

        # Logic lọc format
        best_formats = {}
        
        # Lọc format theo độ phân giải và bitrate, ưu tiên mp4 trước webm
        for f in info.get("formats", []):
            height = f.get("height")
            # Nếu không có height hoặc codec video là "none" (chỉ có audio), bỏ qua
            if not height or f.get("vcodec") == "none":
                continue

            ext = f.get("ext") # định dạng file (mp4, webm, v.v.)
            if ext not in ("mp4", "webm"):
                continue
            
            # tbr: total bitrate (video + audio), vbr: video bitrate riêng
            bitrate = f.get("tbr") or f.get("vbr") or 0
            key = (ext, height)
            
            # Lần đầu gặp key (ext, height) lưu luôn format này và continue
            if key not in best_formats:
                best_formats[key] = {
                    "format_id": f.get("format_id"),
                    "quality": f"{height}p",
                    "ext": ext,
                    "bitrate": bitrate,
                }
                continue
            
            # Nếu đã có key, so sánh bitrate để chọn format tốt hơn
            if bitrate > best_formats[key]["bitrate"]:
                best_formats[key] = {
                    "format_id": f.get("format_id"),
                    "quality": f"{height}p",
                    "ext": ext,
                    "bitrate": bitrate,
                }

        video_formats = []
        webm_formats = []
        
        for d in best_formats.values():
            fmt = VideoFormat(
                format_id=d["format_id"],
                quality=d["quality"],
                ext=d["ext"]
            )

            if d["ext"] == "mp4":
                video_formats.append(fmt)
            else:
                webm_formats.append(fmt)
           
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
            audio_formats=[
                AudioFormat(bitrate=128, ext="mp3"),
                AudioFormat(bitrate=192, ext="mp3"),
                AudioFormat(bitrate=320, ext="mp3"),
            ],
        )


    async def start_convert_task(self, url: str, target_format: MediaFormat, quality_profile: str) -> str:
        """
        Khởi tạo task chuyển đổi video và đẩy vào Celery queue.

        Args:
            url: URL của video YouTube
            target_format: Định dạng đích (MP3, MP4, WAV, WEBM)
            quality_profile: Chất lượng (ví dụ: 320k cho audio, 1080p cho video)

        Returns:
            str: Task ID được tạo bởi Celery

        Raises:
            Exception: Nếu không thể tạo task trong DB
        """
        from app.tasks.media_tasks import download_video_task

        # Đẩy task vào Celery
        task = download_video_task.delay(url, target_format.value, quality_profile)
        task_id = task.id

        task_data = {
            "_id": task_id,
            "url": url,
            "format": target_format.value,
            "quality": quality_profile,
            "status": "pending",
        }
        await self._repository.create_task(task_data)
        return task_id


    async def get_task_status(self, task_id: str) -> dict:
        """
        Lấy trạng thái và tiến độ của task conversion.

        Args:
            task_id: ID của task Celery

        Returns:
            dict: Thông tin trạng thái task bao gồm progress, status, result/error
        """

        # 1. Kiểm tra MongoDB cho trạng thái cuối
        db_task = await self._repository.get_task_by_id(task_id)

        if db_task and db_task.get("status") in ("completed", "failed"):
            return {
                "task_id": task_id,
                "status": "success" if db_task["status"] == "completed" else "failed",
                "progress": 100.0 if db_task["status"] == "completed" else 0.0,
                "result": db_task if db_task["status"] == "completed" else None,
                "error": db_task.get("error_message"),
            }

        # 2. Nếu đang chạy, lấy progress từ Redis
        redis_progress = await self.redis.get(f"task_progress:{task_id}")
        progress = float(redis_progress) if redis_progress else 0.0

        # 3. Kiểm tra Celery cho trạng thái thực tế
        result = AsyncResult(task_id)
        status = result.status.lower()

        response = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "result": None,
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


    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Chuyển đổi giây thành định dạng H:MM:SS hoặc M:SS."""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"


    @staticmethod
    async def _run_command_async(cmd, task_id=None, realtime=False, redis_client=None):
        """
        Thực thi lệnh async với tùy chọn realtime progress tracking.

        Args:
            cmd: List các command arguments
            task_id: Task ID để track progress (optional)
            realtime: Có track progress realtime không
            redis_client: Redis client để update progress

        Returns:
            tuple: (returncode, stdout, stderr)
        """
        stderr_pipe = asyncio.subprocess.STDOUT if realtime else asyncio.subprocess.PIPE

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=stderr_pipe
        )

        stdout_logs = deque(maxlen=30)
        stderr_data = ""

        try:
            last_update_time = 0
            last_progress = -1
            phase = "video"

            if realtime:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break

                    decoded_line = line.decode(errors="ignore").strip()
                    if not decoded_line:
                        continue

                    stdout_logs.append(decoded_line)

                    # Detect phase
                    if "[download]" in decoded_line and last_progress >= 75:
                        phase = "audio"

                    if "[Merger]" in decoded_line:
                        phase = "merge"
                        if redis_client and task_id:
                            await redis_client.set(f"task_progress:{task_id}", 95.0)

                    match = PROGRESS_REGEX.search(decoded_line)
                    if match and task_id:
                        raw = float(match.group(1))

                        if phase == "video":
                            progress = raw * 0.8
                        elif phase == "audio":
                            progress = 80 + raw * 0.15
                        else:
                            progress = 95.0

                        progress = round(progress, 1)

                        if progress > last_progress and time.time() - last_update_time >= 1:
                            if redis_client:
                                await redis_client.set(f"task_progress:{task_id}", progress)
                            last_progress = progress
                            last_update_time = time.time()
            else:
                stdout, stderr = await process.communicate()
                stdout_logs.extend(stdout.decode().splitlines())
                stderr_data = stderr.decode() if stderr else ""

            await process.wait()

        finally:
            if process.returncode is None:
                process.kill()

        return process.returncode, "\n".join(stdout_logs), stderr_data


    def process_download_sync(self, task_id, url, target_format, quality):
        """
        Xử lý toàn bộ quy trình download và convert video (SYNC version cho Celery).

        Args:
            task_id: ID của task
            url: URL YouTube
            target_format: Định dạng đích
            quality: Chất lượng

        Returns:
            dict: Thông tin file đã convert

        Raises:
            Exception: Nếu có lỗi trong quá trình
        """
        try:
            # 1. Lấy info (sync)
            info = self._fetch_info_sync(url, task_id)

            self._repository.update_task_sync(task_id, {
                "title": info["title"],
                "thumbnail": info["thumbnail"],
                "status": "processing"
            })

            self.redis_sync.set(f"task_progress:{task_id}", 0.0)

            # 2. Build command
            cmd = self._build_command(url, target_format, quality, task_id)

            # 3. Download (sync subprocess)
            code, out, err = self._run_command_sync(
                cmd, task_id, realtime=True, redis_client=self.redis_sync
            )

            if code != 0:
                raise Exception(out[-300:])

            # 4. Find file
            file = self._find_file(task_id)

            return self._complete_sync(task_id, file, info, target_format)

        except Exception as e:
            self._repository.update_task_sync(task_id, {
                "status": "failed",
                "error_message": str(e)
            })
            self.redis_sync.delete(f"task_progress:{task_id}")
            raise


    def _fetch_info_sync(self, url, task_id):
        """
        Lấy thông tin cơ bản của video (title, thumbnail) - SYNC version.

        Args:
            url: URL YouTube
            task_id: Task ID (cho logging)

        Returns:
            dict: {"title": str, "thumbnail": str}

        Raises:
            Exception: Nếu yt-dlp lỗi
        """
        import subprocess

        cmd = [
            self.yt_dlp_path,
            "--quiet",
            "--no-warnings",
            "--print-json",
            "--skip-download",
            "--no-playlist",
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception("Lỗi lấy info")

        data = json.loads(result.stdout[result.stdout.find('{'):result.stdout.rfind('}') + 1])

        return {
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail")
        }


    def _run_command_sync(self, cmd, task_id=None, realtime=False, redis_client=None):
        """
        Thực thi lệnh sync với tùy chọn realtime progress tracking.

        Args:
            cmd: List các command arguments
            task_id: Task ID để track progress (optional)
            realtime: Có track progress realtime không
            redis_client: Redis client để update progress

        Returns:
            tuple: (returncode, stdout, stderr)
        """
        import subprocess

        if realtime:
            # Run with realtime progress tracking
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr to stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            stdout_logs = deque(maxlen=30)
            last_update_time = 0
            last_progress = -1
            phase = "video"

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break

                if line:
                    line = line.strip()
                    stdout_logs.append(line)

                    # Detect phase
                    if "[download]" in line and last_progress >= 75:
                        phase = "audio"

                    if "[Merger]" in line:
                        phase = "merge"
                        if redis_client and task_id:
                            redis_client.set(f"task_progress:{task_id}", 95.0)

                    match = PROGRESS_REGEX.search(line)
                    if match and task_id:
                        raw = float(match.group(1))

                        if phase == "video":
                            progress = raw * 0.8
                        elif phase == "audio":
                            progress = 80 + raw * 0.15
                        else:
                            progress = 95.0

                        progress = round(progress, 1)

                        if progress > last_progress and time.time() - last_update_time >= 1:
                            if redis_client:
                                redis_client.set(f"task_progress:{task_id}", progress)
                            last_progress = progress
                            last_update_time = time.time()

            returncode = process.returncode
            return returncode, "\n".join(stdout_logs), ""
        else:
            # Simple sync run
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode, result.stdout, result.stderr


    def _complete_sync(self, task_id, file, info, fmt):
        """
        Hoàn thành task và cập nhật database - SYNC version.

        Args:
            task_id: Task ID
            file: Path đến file đã convert
            info: Dict chứa title, thumbnail
            fmt: Định dạng file

        Returns:
            dict: Thông tin kết quả
        """
        result = {
            "status": "completed",
            "task_id": task_id,
            "file_name": f"{info['title']}.{fmt}",
            "file_path": str(file),
            "download_url": f"{settings.STATIC_FILES_URL}/downloads/{file.name}"
        }

        self._repository.update_task_sync(task_id, {
            "status": "completed",
            "progress": 100.0,
            "file_path": str(file),
            "file_name": result["file_name"],
            "download_url": result["download_url"]
        })

        self.redis_sync.set(f"task_progress:{task_id}", 100.0)

        return result


    async def process_download(self, task_id, url, target_format, quality):
        """
        Xử lý toàn bộ quy trình download và convert video.

        Args:
            task_id: ID của task
            url: URL YouTube
            target_format: Định dạng đích
            quality: Chất lượng

        Returns:
            dict: Thông tin file đã convert

        Raises:
            Exception: Nếu có lỗi trong quá trình
        """
        try:
            # 1. Lấy info
            info = await self._fetch_info(url, task_id)

            await self._repository.update_task(task_id, {
                "title": info["title"],
                "thumbnail": info["thumbnail"],
                "status": "processing"
            })

            await self.redis.set(f"task_progress:{task_id}", 0.0)

            # 2. Build command
            cmd = self._build_command(url, target_format, quality, task_id)

            # 3. Download
            code, out, err = await self._run_command_async(
                cmd, task_id, realtime=True, redis_client=self.redis
            )

            if code != 0:
                raise Exception(out[-300:])

            # 4. Find file
            file = self._find_file(task_id)

            return await self._complete(task_id, file, info, target_format)

        except Exception as e:
            await self._repository.update_task(task_id, {
                "status": "failed",
                "error_message": str(e)
            })
            await self.redis.delete(f"task_progress:{task_id}")
            raise


    async def _fetch_info(self, url, task_id):
        """
        Lấy thông tin cơ bản của video (title, thumbnail).

        Args:
            url: URL YouTube
            task_id: Task ID (cho logging)

        Returns:
            dict: {"title": str, "thumbnail": str}

        Raises:
            Exception: Nếu yt-dlp lỗi
        """
        cmd = [
            self.yt_dlp_path,
            "--quiet",
            "--no-warnings",
            "--print-json",
            "--skip-download",
            "--no-playlist",
            url
        ]

        code, out, _ = await self._run_command_async(cmd, task_id)

        if code != 0:
            raise Exception("Lỗi lấy info")

        data = json.loads(out[out.find('{'):out.rfind('}') + 1])

        return {
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail")
        }


    def _build_command(self, url, fmt, quality, task_id):
        """
        Xây dựng command yt-dlp dựa trên format và quality.

        Args:
            url: URL YouTube
            fmt: Định dạng đích (mp3, mp4, etc.)
            quality: Chất lượng (320k, 1080p, etc.)
            task_id: Task ID để đặt tên file

        Returns:
            list: Command arguments cho yt-dlp
        """
        output = str(self.download_path / task_id) + ".%(ext)s"

        cmd = [
            self.yt_dlp_path,
            "--no-playlist",
            "--newline",
            "--progress",
            "-o", output
        ]

        if fmt in ("mp3", "wav"):
            bitrate = quality.replace("k", "")
            cmd += ["-x", "--audio-format", fmt, "--audio-quality", bitrate]
        else:
            height = quality.replace("p", "")
            f = f"bestvideo[height<={height}]+bestaudio/best"
            cmd += ["-f", f, "--merge-output-format", fmt]

        return cmd + [url]

    def _find_file(self, task_id):
        """
        Tìm file đã download dựa trên task_id.

        Args:
            task_id: Task ID

        Returns:
            Path: Đường dẫn đến file

        Raises:
            Exception: Nếu không tìm thấy file
        """
        file = next(self.download_path.glob(f"{task_id}.*"), None)
        if not file:
            raise Exception("Không tìm thấy file")
        return file


    async def _complete(self, task_id, file, info, fmt):
        """
        Hoàn thành task và cập nhật database.

        Args:
            task_id: Task ID
            file: Path đến file đã convert
            info: Dict chứa title, thumbnail
            fmt: Định dạng file

        Returns:
            dict: Thông tin kết quả
        """
        result = {
            "status": "completed",
            "task_id": task_id,
            "file_name": f"{info['title']}.{fmt}",
            "file_path": str(file),
            "download_url": f"{settings.STATIC_FILES_URL}/downloads/{file.name}"
        }

        await self._repository.update_task(task_id, {
            "status": "completed",
            "progress": 100.0,
            "file_path": str(file),
            "file_name": result["file_name"],
            "download_url": result["download_url"]
        })

        await self.redis.set(f"task_progress:{task_id}", 100.0)

        return result
