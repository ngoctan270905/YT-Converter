import sys
import os
from pathlib import Path

# Thêm project root vào sys.path để có thể import app từ main.py
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator

@pytest.fixture(scope="session")
def event_loop():
    """Tạo instance của default event loop cho toàn bộ session test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture cung cấp AsyncClient để gọi API FastAPI trong quá trình test.
    Sử dụng ASGITransport để test trực tiếp trên app mà không cần chạy server.
    """
    from main import app # Import ở đây sau khi path đã được set
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://testserver"
    ) as ac:
        yield ac
