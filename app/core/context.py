from contextvars import ContextVar
from typing import Optional

# Khai báo các ContextVar để lưu trữ metadata của request
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
client_ip_ctx: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
user_agent_ctx: ContextVar[Optional[str]] = ContextVar("user_agent", default=None)


def get_request_id() -> Optional[str]:
    """
    Lấy request_id của request hiện tại từ ContextVar.

    Returns
    -------
    Optional[str]
        Giá trị request_id nếu đã được thiết lập,
        ngược lại trả về None.

    Ghi chú
    -------
    ContextVar đảm bảo mỗi request (kể cả trong môi trường async)
    có một giá trị riêng biệt, tránh xung đột dữ liệu giữa các request.
    """
    return request_id_ctx.get()


def set_request_id(request_id: str):
    """
    Thiết lập request_id cho request hiện tại.

    Parameters
    ----------
    request_id : str
        Mã định danh duy nhất của request.
        Thường được tạo ở middleware để phục vụ logging và tracing.
    """
    request_id_ctx.set(request_id)


def get_client_ip() -> Optional[str]:
    """
    Lấy địa chỉ IP của client từ ContextVar.

    Returns
    -------
    Optional[str]
        Địa chỉ IP của client nếu đã được thiết lập,
        ngược lại trả về None.
    """
    return client_ip_ctx.get()


def set_client_ip(ip: str):
    """
    Thiết lập địa chỉ IP của client cho request hiện tại.

    Parameters
    ----------
    ip : str
        Địa chỉ IP của client, thường được lấy từ request
        trong middleware.
    """
    client_ip_ctx.set(ip)


def get_user_agent() -> Optional[str]:
    """
    Lấy thông tin User-Agent của client từ ContextVar.

    Returns
    -------
    Optional[str]
        Chuỗi User-Agent nếu đã được thiết lập,
        ngược lại trả về None.
    """
    return user_agent_ctx.get()


def set_user_agent(ua: str):
    """
    Thiết lập thông tin User-Agent cho request hiện tại.

    Parameters
    ----------
    ua : str
        Chuỗi User-Agent của client, thường được lấy từ header HTTP.
    """
    user_agent_ctx.set(ua)