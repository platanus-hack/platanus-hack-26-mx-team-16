from typing import Any


class DomainError(Exception):
    code: str
    message: str
    status_code: int
    context: dict[str, Any] | None = None

    def __init__(self, code: str, message: str, status_code: int = 400, context: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.context = context
        super().__init__(message)

