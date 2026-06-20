from dataclasses import dataclass


@dataclass
class AsyncTask:
    operation: str
    is_success: bool
    reason: str = None

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} operation={self.operation} status={self.status_label}>"

    @property
    def status_label(self) -> str:
        return "SUCCESS" if self.is_success else "FAILURE"

    @property
    def to_dict(self) -> dict:
        response_data = {
            "operation": self.operation,
            "status": self.status_label,
        }
        if self.reason:
            response_data["reason"] = self.reason
        return response_data

    @property
    def to_logs(self) -> str:
        return f"operation={self.operation} status={self.status_label}"
