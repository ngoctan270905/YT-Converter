# Lộ trình Tối ưu Backend lên Production (Theo thứ tự ưu tiên)

Tài liệu này sắp xếp 11 vấn đề kỹ thuật theo thứ tự cần thực hiện từ quan trọng nhất đến các bước tối ưu sau cùng.

---

## 🔥 GIAI ĐOẠN 1: NỀN TẢNG & BẢO MẬT (Cần sửa ngay)

### 1. Treo Event Loop (Blocking Event Loop) - **QUAN TRỌNG NHẤT**
*   **Vấn đề:** Dùng `subprocess.run` làm treo toàn bộ web server khi có người tải video.
*   **Giải pháp:** Chuyển sang `asyncio.create_subprocess_exec`. Đây là điều kiện tiên quyết để server phục vụ được nhiều hơn 1 người.

### 2. Lỗ hổng Command Injection
*   **Vấn đề:** Nhận trực tiếp format/quality từ user truyền vào lệnh shell.
*   **Giải pháp:** Dùng Pydantic Enum để whitelist đầu vào. Bảo mật là ưu tiên hàng đầu trước khi công khai API.

### 3. Xung đột môi trường (Hardcoded Paths)
*   **Vấn đề:** Hardcode ổ `F:/ffmpeg`. Lên Linux/Docker sẽ chết app ngay lập tức.
*   **Giải pháp:** Đưa mọi đường dẫn vào `.env` và dùng `pathlib`.

### 4. Lỗi ký tự đặc biệt trong tên file
*   **Vấn đề:** Dùng tiêu đề video làm tên file gây lỗi OS và lỗi logic tìm kiếm.
*   **Giải pháp:** Đổi sang dùng **UUID** làm tên file vật lý.

---

## ⚡ GIAI ĐOẠN 2: QUẢN LÝ TÀI NGUYÊN (Để chịu tải)

### 5. Tràn ổ đĩa (Disk Space Exhaustion)
*   **Vấn đề:** File không bao giờ xóa, server sẽ sập sau vài ngày chạy.
*   **Giải pháp:** Viết Background Task tự động dọn dẹp file sau 24h.

### 6. Cạn kiệt tài nguyên (CPU & RAM)
*   **Vấn đề:** Nhiều người convert cùng lúc gây treo server.
*   **Giải pháp:** Dùng `asyncio.Semaphore` để giới hạn số lượng task xử lý đồng thời.

### 7. Lỗi Timeout HTTP (Gateway Timeout 504)
*   **Vấn đề:** Video dài xử lý lâu làm ngắt kết nối trình duyệt.
*   **Giải pháp:** Chuyển API sang dạng bất đồng bộ (trả về `task_id` ngay).

---

## 🛠️ GIAI ĐOẠN 3: TỐI ƯU HÓA & TRẢI NGHIỆM (Hoàn thiện)

### 8. Tiến trình "mồ côi" (Orphan Processes)
*   **Vấn đề:** User hủy request nhưng server vẫn tốn CPU xử lý tiếp.
*   **Giải pháp:** Theo dõi `is_disconnected()` để kill subprocess.

### 9. IP bị YouTube chặn (Rate Limiting)
*   **Vấn đề:** YouTube chặn IP của server.
*   **Giải pháp:** Tích hợp Proxy hoặc cấu hình xoay vòng IP.

### 10. Thiếu thông báo tiến trình (Progress Tracking)
*   **Vấn đề:** User không biết đang tải được bao nhiêu %.
*   **Giải pháp:** Parse `stdout` của yt-dlp và gửi qua WebSocket.

### 11. Lộ thông tin nhạy cảm trong Log
*   **Vấn đề:** Log chứa URL nhạy cảm.
*   **Giải pháp:** Cấu hình Filter cho Loguru.

---
*Lộ trình được xây dựng bởi Gemini CLI - 2026-04-09*
