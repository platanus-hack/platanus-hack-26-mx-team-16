from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, Field

from src.common.domain.entities.common.pagination import Pagination


class ApiResponse[T](BaseModel):
    data: T
    pagination: Pagination | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        json_encoders: ClassVar = {datetime: lambda v: v.isoformat() if isinstance(v, datetime) else str(v)}
