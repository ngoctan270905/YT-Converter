from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

DataType = TypeVar("DataType")

class UnifiedResponse(BaseModel, Generic[DataType]):
    """
    A generic response model for all API endpoints.
    """
    success: bool = True
    message: Optional[str] = None
    data: Optional[DataType] = None
