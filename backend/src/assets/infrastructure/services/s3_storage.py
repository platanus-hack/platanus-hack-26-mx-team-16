from botocore.exceptions import ClientError

from src.assets.domain.services.storage import StorageService
from src.common.domain.entities.common.in_memory_file import InMemoryFile
from src.common.settings import settings
from src.storage.infrastructure.s3_client import get_s3_client


class S3StorageService(StorageService):
    def __init__(self):
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def upload_file(self, input_file: InMemoryFile) -> InMemoryFile:
        if not input_file.is_procesable:
            error_msg = "Input file must have both file_path and file_bytes"
            raise ValueError(error_msg)

        object_key = input_file.file_key or input_file.file_path

        try:
            get_s3_client().put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=input_file.file_bytes,
            )

            return InMemoryFile(
                file_path=object_key,
                file_bytes=input_file.file_bytes,
                file_base64=input_file.file_base64,
            )

        except ClientError as e:
            error_msg = f"Failed to upload file to S3: {e!s}"
            raise ValueError(error_msg) from e

    def get_file(self, file_path: str) -> InMemoryFile:
        # Extract bucket and key from S3 URL if provided
        if file_path.startswith("s3://"):
            # Parse S3 URL format: s3://bucket/key
            path_without_prefix = file_path[5:]  # Remove "s3://"
            parts = path_without_prefix.split("/", 1)
            if len(parts) == 2:
                bucket_name, object_key = parts
            else:
                raise ValueError(f"Invalid S3 URL format: {file_path}")
        else:
            # Assume it's just the object key
            bucket_name = self.bucket_name
            object_key = file_path

        try:
            response = get_s3_client().get_object(
                Bucket=bucket_name,
                Key=object_key,
            )

            file_bytes = response["Body"].read()

            return InMemoryFile(
                file_path=file_path if file_path.startswith("s3://") else f"s3://{bucket_name}/{object_key}",
                file_bytes=file_bytes,
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {object_key}") from e
            raise ValueError(f"Failed to retrieve file from S3: {e!s}") from e

    def delete_file(self, file_path: str) -> None:
        # Handle different URL formats
        if file_path.startswith("http://") or file_path.startswith("https://"):
            # Extract object key from HTTP URL
            # Format: https://domain.com/bucket/path/to/file or https://domain.com/path/to/file
            from urllib.parse import urlparse

            parsed_url = urlparse(file_path)
            # Remove leading slash and extract the path
            object_key = parsed_url.path.lstrip("/")

            # If the path starts with the bucket name, remove it
            if object_key.startswith(f"{self.bucket_name}/"):
                object_key = object_key[len(self.bucket_name) + 1 :]

            bucket_name = self.bucket_name
        elif file_path.startswith("s3://"):
            path_without_prefix = file_path[5:]  # Remove "s3://"
            parts = path_without_prefix.split("/", 1)
            if len(parts) == 2:
                bucket_name, object_key = parts
            else:
                raise ValueError(f"Invalid S3 URL format: {file_path}")
        else:
            bucket_name = self.bucket_name
            object_key = file_path

        try:
            get_s3_client().delete_object(
                Bucket=bucket_name,
                Key=object_key,
            )
        except ClientError as e:
            error_msg = f"Failed to delete file from S3: {e!s}"
            raise ValueError(error_msg) from e
