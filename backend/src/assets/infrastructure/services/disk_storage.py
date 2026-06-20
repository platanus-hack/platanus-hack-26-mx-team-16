import os
from pathlib import Path

from src.assets.domain.services.storage import StorageService
from src.common.domain.entities.common.in_memory_file import InMemoryFile
from src.common.settings import settings


class DiskStorageService(StorageService):
    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or getattr(settings, "LOCAL_STORAGE_PATH", "storage")).resolve()

        # Ensure the base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload_file(self, input_file: InMemoryFile) -> InMemoryFile:
        if not input_file.is_procesable:
            error_msg = "Input file must have both file_path and file_bytes"
            raise ValueError(error_msg)

        # Get the file name from the input path
        file_name = input_file.file_name or "unnamed_file"

        # Create a safe file path relative to base_path
        # Remove any path traversal attempts
        safe_file_name = os.path.basename(file_name)

        # Build the full file path
        full_path = self.base_path / safe_file_name

        # Handle file name conflicts by appending a number
        counter = 0
        original_path = full_path
        while full_path.exists():
            counter += 1
            stem = original_path.stem
            suffix = original_path.suffix
            full_path = original_path.parent / f"{stem}_{counter}{suffix}"

        try:
            # Write the file to disk
            full_path.write_bytes(input_file.file_bytes)

            # Return the file with the disk path
            return InMemoryFile(
                file_path=f"file://{full_path}",
                file_bytes=input_file.file_bytes,
                file_base64=input_file.file_base64,
            )

        except OSError as e:
            error_msg = f"Failed to write file to disk: {e!s}"
            raise OSError(error_msg) from e

    def get_file(self, file_path: str) -> InMemoryFile:
        # Parse the file path
        if file_path.startswith("file://"):
            # Remove file:// prefix
            actual_path = Path(file_path[7:])
        elif os.path.isabs(file_path):
            # Absolute path
            actual_path = Path(file_path)
        else:
            # Relative path - resolve relative to base_path
            actual_path = self.base_path / file_path

        # Resolve to absolute path
        actual_path = actual_path.resolve()

        # Security check: ensure path is within base_path or explicitly allowed
        try:
            # Check if the path is within base_path
            actual_path.relative_to(self.base_path)
        except ValueError:
            # Path is outside base_path - only allow if it was an absolute path
            if not (file_path.startswith("file://") or os.path.isabs(file_path)):
                error_msg = f"Access denied: Path {actual_path} is outside storage directory"
                raise PermissionError(error_msg)

        # Check if file exists
        if not actual_path.exists():
            error_msg = f"File not found: {actual_path}"
            raise FileNotFoundError(error_msg)

        if not actual_path.is_file():
            error_msg = f"Path is not a file: {actual_path}"
            raise ValueError(error_msg)

        try:
            # Read the file from disk
            file_bytes = actual_path.read_bytes()

            return InMemoryFile(
                file_path=f"file://{actual_path}",
                file_bytes=file_bytes,
            )

        except OSError as e:
            error_msg = f"Failed to read file from disk: {e!s}"
            raise OSError(error_msg) from e

    def delete_file(self, file_path: str) -> None:
        if file_path.startswith("file://"):
            actual_path = Path(file_path[7:])
        elif os.path.isabs(file_path):
            actual_path = Path(file_path)
        else:
            actual_path = self.base_path / file_path

        actual_path = actual_path.resolve()
        try:
            actual_path.relative_to(self.base_path)
        except ValueError:
            if not (file_path.startswith("file://") or os.path.isabs(file_path)):
                error_msg = f"Access denied: Path {actual_path} is outside storage directory"
                raise PermissionError(error_msg)
        if not actual_path.exists():
            return

        if not actual_path.is_file():
            error_msg = f"Path is not a file: {actual_path}"
            raise ValueError(error_msg)
        try:
            actual_path.unlink()
        except OSError as e:
            error_msg = f"Failed to delete file from disk: {e!s}"
            raise OSError(error_msg) from e
