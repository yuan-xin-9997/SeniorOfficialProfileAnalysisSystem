from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None
    timestamp: str = datetime.now(timezone.utc).isoformat()


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def success(data: Any = None, message: str = "success", code: int = 200) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
