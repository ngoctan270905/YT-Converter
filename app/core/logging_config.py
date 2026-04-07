import logging
import sys
import os
from loguru import logger
from app.core.config import settings
from app.core.context import get_request_id, get_client_ip, get_user_agent


class InterceptHandler(logging.Handler):
    """
    Custom logging handler dùng để chuyển hướng (intercept)
    toàn bộ log từ thư viện logging chuẩn của Python (stdlib)
    sang hệ thống Loguru.

    Mục đích:
    - Đồng bộ toàn bộ logging trong hệ thống về một chuẩn duy nhất (Loguru)
    - Đảm bảo log từ uvicorn, fastapi, sqlalchemy, v.v. đều được xử lý thống nhất
    - Giữ nguyên level log và stacktrace

    Cơ chế hoạt động:
    - Nhận một logging.LogRecord từ stdlib
    - Chuyển đổi level sang level tương ứng của Loguru
    - Tính toán lại stack depth để Loguru hiển thị đúng file và dòng
    - Ghi log thông qua logger.opt(...)
    """

    def emit(self, record: logging.LogRecord) -> None:
        """
        Override phương thức emit của logging.Handler.

        Parameters
        ----------
        record : logging.LogRecord
            Đối tượng log record do logging module tạo ra.

        Flow:
        1. Lấy level tương ứng của Loguru
        2. Tính lại stack frame depth để không hiển thị logging nội bộ
        3. Forward log sang Loguru
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def inject_request_context(record):
    """
    Patch function dùng để inject request context vào mỗi log record.

    Hàm này sẽ được Loguru gọi trước khi ghi log
    (thông qua logger.configure(patchings=[...]))

    Context được thêm:
    - request_id  : ID của request hiện tại (traceability)
    - client_ip   : IP của client gửi request
    - user_agent  : Trình duyệt hoặc client gửi request

    Parameters
    ----------
    record : dict
        Log record dạng dict nội bộ của Loguru.

    Returns
    -------
    bool
        Luôn trả về True để Loguru tiếp tục xử lý log.

    Lưu ý:
    - Hàm được bọc try/except để tránh crash logger nếu context lỗi.
    - record["extra"] được sử dụng để inject metadata.
    """
    try:
        rid = get_request_id()
        if rid:
            record["extra"]["request_id"] = rid

        cip = get_client_ip()
        if cip:
            record["extra"]["client_ip"] = cip

        ua = get_user_agent()
        if ua:
            record["extra"]["user_agent"] = ua

    except Exception:
        # Không để logging bị crash vì lỗi context
        pass

    return True


def configure_logging():
    """
    Cấu hình toàn bộ hệ thống logging cho application.

    Chức năng chính:
    ----------------
    1. Xóa toàn bộ handler mặc định của Loguru
    2. Cấu hình console logging
    3. Cấu hình file logging (có rotation, retention, compression)
    4. Patch Loguru để inject request context tự động
    5. Intercept toàn bộ logging từ stdlib sang Loguru
    6. Redirect log từ:
        - uvicorn
        - fastapi
        - starlette
        - sqlalchemy

    Behavior theo môi trường:
    ---------------------------
    - Development:
        + Log format đẹp, có màu
        + Không serialize JSON
    - Production:
        + Log dạng JSON (serialize=True)
        + Không color
        + Phù hợp cho ELK, Loki, Datadog,...

    File logging:
    --------------
    - rotation   : 10 MB
    - retention  : 7 ngày
    - compression: zip

    Yêu cầu:
    --------
    Phải được gọi một lần duy nhất khi khởi động application
    (thường trong main.py trước khi tạo FastAPI app).
    """
    logger.remove()

    log_level = settings.LOG_LEVEL.upper()
    log_file = settings.LOG_FILE
    is_production = getattr(settings, "ENVIRONMENT", "development") == "production"

    if log_dir := os.path.dirname(log_file):
        os.makedirs(log_dir, exist_ok=True)

    # Patch logger gốc — tất cả import logger đều được inject context
    logger.configure(patcher=inject_request_context)

    # Console logging
    if is_production:
        logger.add(
            sys.stdout,
            level=log_level,
            enqueue=True,
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=log_level,
            enqueue=True,
            serialize=False,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> | {message}"
            ),
            colorize=True,
        )

    # File logging
    logger.add(
        log_file,
        level=log_level,
        enqueue=True,
        serialize=True,
        rotation=settings.LOG_MAX_BYTES,
        retention=settings.LOG_BACKUP_COUNT,
        compression="zip",
    )

    # Intercept stdlib logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Redirect log của ASGI stack
    for name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "starlette"]:
        _logger = logging.getLogger(name)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False

    # SQLAlchemy — chỉ log WARNING trở lên
    _sq = logging.getLogger("sqlalchemy")
    _sq.handlers = [InterceptHandler()]
    _sq.setLevel(logging.WARNING)
    _sq.propagate = False