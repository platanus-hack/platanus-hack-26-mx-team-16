from src.common.domain.exceptions._base import DomainError


class FileNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="storage.FileNotFound",
            message=f"File not found: {identifier}" if identifier else "File not found",
            status_code=404,
        )


class FileUploadError(DomainError):
    def __init__(self, detail: str = ""):
        super().__init__(
            code="storage.FileUploadError",
            message=f"File upload failed: {detail}" if detail else "File upload failed",
            status_code=500,
        )


class UnsupportedMimeError(DomainError):
    def __init__(self, mime: str, allowed: list[str]):
        super().__init__(
            code="storage.UnsupportedMime",
            message=f"Unsupported file type '{mime}'. Allowed: {', '.join(allowed)}",
            status_code=415,
        )


class FileTooLargeError(DomainError):
    def __init__(self, size: int, max_size: int):
        super().__init__(
            code="storage.FileTooLarge",
            message=f"File too large: {size} bytes (max {max_size} bytes)",
            status_code=413,
        )
