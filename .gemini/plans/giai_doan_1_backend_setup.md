# Giai đoạn 1: Thiết lập Backend và Logic cốt lõi

Đây là quy trình làm việc chi tiết cho Giai đoạn 1 của dự án chuyển đổi YouTube.

## Các bước

1.  **Cài đặt công cụ bên ngoài**:
    *   Đảm bảo `yt-dlp` và `ffmpeg` được cài đặt trên hệ thống hoặc trong môi trường triển khai.
        *   **Kiểm tra cài đặt**:
            *   Mở Command Prompt hoặc PowerShell.
            *   Gõ `yt-dlp --version` và nhấn Enter. Nếu nó hiển thị số phiên bản, `yt-dlp` đã được cài đặt.
            *   Gõ `ffmpeg -version` và nhấn Enter. Nếu nó hiển thị thông tin phiên bản, `ffmpeg` đã được cài đặt.
        *   **Cài đặt `yt-dlp` trên Windows**:
            *   Tải xuống `yt-dlp.exe` từ trang phát hành chính thức của `yt-dlp` trên GitHub: [https://github.com/yt-dlp/yt-dlp/releases](https://github.com/yt-dlp/yt-dlp/releases)
            *   Đặt tệp `yt-dlp.exe` vào một thư mục có trong biến môi trường PATH của hệ thống (ví dụ: `C:\Windows`, hoặc một thư mục bạn tạo riêng và thêm vào PATH).
        *   **Cài đặt `ffmpeg` trên Windows**:
            *   Tải xuống phiên bản Windows của `ffmpeg` từ trang web chính thức: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) (chọn một bản dựng từ các nhà cung cấp được đề xuất, ví dụ: gyan.dev hoặc BtbN).
            *   Giải nén tệp zip đã tải xuống. Bạn sẽ nhận được một thư mục (ví dụ: `ffmpeg-N.N.N-full_build-shared`).
            *   Di chuyển thư mục này đến một vị trí dễ quản lý (ví dụ: `C:\ffmpeg`).
            *   Thêm đường dẫn đến thư mục `bin` bên trong thư mục `ffmpeg` vào biến môi trường PATH của hệ thống (ví dụ: nếu bạn giải nén vào `C:\ffmpeg`, hãy thêm `C:\ffmpeg\bin` vào PATH).
            *   Để thêm vào PATH trên Windows: Tìm kiếm "Environment Variables" -> "Edit the system environment variables" -> "Environment Variables..." -> Trong phần "System variables", tìm biến "Path", chọn "Edit" -> "New" và thêm đường dẫn của bạn.
2.  **Thiết lập dự án FastAPI**:
    *   Tạo các endpoint API cơ bản (`/convert`, `/status`, `/download`).
    *   Định nghĩa các Pydantic schemas cho đầu vào yêu cầu (URL, format, quality) và đầu ra phản hồi (job ID, status, download link).
3.  **Tích hợp `yt-dlp` và `ffmpeg`**:
    *   Viết các hàm xử lý để gọi `yt-dlp` để tải xuống video.
    *   Viết các hàm để gọi `ffmpeg` để chuyển đổi tệp đã tải xuống sang định dạng mục tiêu.
4.  **Triển khai hàng đợi tác vụ với Celery**:
    *   Cài đặt Celery và Redis/RabbitMQ.
    *   Định nghĩa các Celery task để xử lý tải xuống và chuyển đổi video trong nền.
    *   Thay đổi các endpoint API để đẩy tác vụ vào hàng đợi và trả về một job ID.
5.  **Quản lý trạng thái tác vụ**:
    *   Sử dụng Celery để theo dõi trạng thái của các tác vụ (đang chờ, đang xử lý, hoàn thành, thất bại).
    *   Lưu trữ trạng thái và đường dẫn tệp đã chuyển đổi vào một nơi nào đó (ví dụ: bộ nhớ cache Redis, hoặc MongoDB nếu cần lưu trữ lâu dài).