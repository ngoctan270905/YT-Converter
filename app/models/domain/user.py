from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class User(BaseModel):
    """
    Domain model for User stored in MongoDB.
    Sử dụng Pydantic v2 ConfigDict và chuẩn hóa UTC.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "fullname": "John Doe",
                "email": "johndoe@example.com",
                "phone_number": "0901234567",
                "is_active": True,
                "role": "user",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
    )

    id: str | None = Field(None, alias="_id")
    fullname: str = Field(..., min_length=3, max_length=50)
    email: str = Field(...)
    phone_number: str = Field(..., min_length=10, max_length=15)
    hashed_password: str
    is_active: bool = True
    role: str = "user"
    avatar_url: str | None = Field(None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

