import json
import asyncio
import subprocess
from pathlib import Path
from collections import defaultdict

from app.core.config import settings
from app.schemas.media import MediaInfoResponse, VideoFormat, AudioFormat


class MediaService:
    """Service xử lý logic liên quan đến đa phương tiện (tải, chuyển đổi, lấy thông tin)."""

    def __init__(self):
        self.download_path = Path(settings.DOWNLOADS_DIR)
        self.download_path.mkdir(parents=True, exist_ok=True)


    def _format_duration(self, seconds: int | None) -> str:
        """Định dạng thời lượng từ giây sang định dạng dễ đọc (h:mm:ss hoặc m:ss)."""
        if not seconds:
            return "0:00"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


    async def get_video_info(self, url: str) -> MediaInfoResponse:
        """Lấy thông tin video chi tiết từ URL sử dụng yt-dlp."""
        
        # Chuẩn bị lệnh yt-dlp để lấy thông tin video dưới dạng JSON
        cmd = [
            settings.YT_DLP_PATH,
            "--quiet",
            "--no-warnings",
            "--js-runtimes", "node",
            "--print-json",
            "--skip-download",
            "--no-playlist",
            url,
        ]
        
        # Hàm chạy yt-dlp trong một thread riêng để tránh blocking event loop
        def run_yt_dlp():
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
         
        loop = asyncio.get_event_loop()
        # run_in_executor sẽ chạy hàm run_yt_dlp trong một thread pool và trả về kết quả khi hoàn thành
        result = await loop.run_in_executor(None, run_yt_dlp) 
        
        # Kiểm tra lỗi từ yt-dlp
        if result.returncode != 0:
            error_msg = result.stderr.decode().strip()
            raise Exception(f"YT-DLP Error: {error_msg}")
        
        # Giải mã kết quả JSON từ yt-dlp
        info = json.loads(result.stdout.decode())

        # Chọn format bitrate cao nhất cho mỗi độ phân giải
        best_formats = defaultdict(dict)
        
        # Lặp qua tất cả các format và chọn format tốt nhất cho mỗi độ phân giải
        for f in info.get("formats", []):
            height = f.get("height") 
    
            if not height or f.get("vcodec") == "none":
                continue 

            ext = f.get("ext")
            if ext not in ("mp4", "webm"):
                continue
            
            bitrate = f.get("tbr") or f.get("vbr") or 0
            key = (ext, height)
            
            # Nếu chưa có format nào cho độ phân giải này hoặc bitrate của format hiện tại cao hơn, cập nhật format tốt nhất
            if not best_formats.get(key) or bitrate > best_formats[key].get("bitrate", 0):
                best_formats[key] = {
                    "format_id": f.get("format_id"),
                    "quality": f"{height}p",
                    "ext": ext,
                    "bitrate": bitrate,
                }
        
        video_formats = []
        webm_formats = []
        
        # Sắp xếp các format đã chọn vào danh sách tương ứng
        for (ext, height), data in best_formats.items():
            
            fmt = VideoFormat(
                format_id=data["format_id"],
                quality=data["quality"],
                ext=data["ext"]
            )
            if ext == "mp4":
                video_formats.append(fmt)
            else:
                webm_formats.append(fmt)
        
        # Sắp xếp các format theo độ phân giải từ cao đến thấp
        video_formats.sort(key=lambda x: int(x.quality.replace("p", "")), reverse=True) 
        webm_formats.sort(key=lambda x: int(x.quality.replace("p", "")), reverse=True)
        
        # Định nghĩa các format âm thanh phổ biến với bitrate khác nhau
        audio_formats = [
            AudioFormat(bitrate=128, ext="mp3"),
            AudioFormat(bitrate=192, ext="mp3"),
            AudioFormat(bitrate=320, ext="mp3"),
        ]

        return MediaInfoResponse(
            title=info.get("title", "Unknown"),
            thumbnail=info.get("thumbnail"),
            duration=info.get("duration"),
            duration_text=self._format_duration(info.get("duration")),
            author=info.get("uploader"),
            views=info.get("view_count"),
            upload_date=info.get("upload_date"),
            url=url,
            video_formats=video_formats,
            webm_formats=webm_formats,
            audio_formats=audio_formats,
        )

    async def process_media(self, url: str, target_format: str, quality_profile: str) -> dict:
        """Thực hiện tải và chuyển đổi file."""
        
        video_id = await self._get_video_id(url)
        
        output_template = str(self.download_path / "%(title)s [%(id)s - %(height)sp].%(ext)s")
        
        # Chuẩn bị lệnh yt-dlp để tải và chuyển đổi video theo yêu cầu
        cmd = [
            settings.YT_DLP_PATH,
            "--no-playlist",
            "--no-warnings",
            "--progress",
            "-o", output_template,
        ]
        
        # Nếu định dạng yêu cầu là mp3, sử dụng các tùy chọn đặc biệt để trích xuất âm thanh và chuyển đổi sang mp3
        if target_format == "mp3":
            if target_format == "mp3":
                cmd.extend([
                    "-f", "bestaudio/best",
                    "-x",
                    "--audio-format", "mp3",
                    "--audio-quality", quality_profile,
                ])
        # Ngược lại, nếu là định dạng video, chọn format tốt nhất dựa trên profile chất lượng và định dạng yêu cầu
        else:
            format_spec = f"{quality_profile}+bestaudio/best"
            
            cmd.extend([
                "-f", format_spec,
                "--merge-output-format", target_format,
            ])
        
        # 
        if settings.FFMPEG_PATH:
            cmd.extend(["--ffmpeg-location", settings.FFMPEG_PATH])

        cmd.append(url)
        
        # Hàm chạy lệnh tải và chuyển đổi trong một thread riêng để tránh blocking event loop
        def run_download():
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_download)
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            print(f"DOWNLOAD ERROR: {error_msg}")
            raise Exception(f"Download Error: {error_msg}")
        
        # Tìm file đã tải xong dựa trên video_id và định dạng yêu cầu
        downloaded_file = self._find_downloaded_file(video_id, target_format)
        if not downloaded_file:
            raise Exception("Không tìm thấy file sau khi tải xong.")

        return {
            "file_path": str(downloaded_file),
            "file_name": downloaded_file.name,
            "file_size": downloaded_file.stat().st_size,
            "download_url": f"{settings.STATIC_FILES_URL}/downloads/{downloaded_file.name}",
        }
  

    async def _get_video_id(self, url: str) -> str:
        """Lấy video_id từ URL sử dụng yt-dlp."""

        cmd = [settings.YT_DLP_PATH, "--get-id", "--no-playlist", url]
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        )
        return result.stdout.strip()


    def _find_downloaded_file(self, video_id: str, target_ext: str) -> Path | None:
        """Tìm file đã tải xong dựa trên video_id và định dạng yêu cầu."""
        
        pattern = f"*{video_id}*"
        for file in self.download_path.glob(pattern):
            if file.suffix.lower() == f".{target_ext.lower()}":
                return file
        return None