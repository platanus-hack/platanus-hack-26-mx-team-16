from pydantic import BaseModel

from src.common.domain.enums.common import TaskStatus


class TaskResult(BaseModel):
    status: TaskStatus
    message: str | None = None

    @property
    def to_dict(self):
        data = {
            "status": str(self.status),
        }
        if self.message:
            data["message"] = self.message
        return data

    @classmethod
    def success(cls, message: str | None = None) -> "TaskResult":
        return cls(
            status=TaskStatus.SUCCESS,
            message=message,
        )

    @classmethod
    def failure(cls, message: str | None = None) -> "TaskResult":
        return cls(
            status=TaskStatus.FAILURE,
            message=message,
        )
