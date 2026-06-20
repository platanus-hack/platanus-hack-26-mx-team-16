"""Router for the File Storage module."""

from fastapi import APIRouter

from src.storage.presentation.endpoints.files import (
    delete_file,
    download_file,
    get_file,
    upload_file,
)

storage_router = APIRouter(prefix="/documents", tags=["Documents"])

storage_router.add_api_route(
    "/upload",
    upload_file,
    methods=["POST"],
    summary="Upload file",
    description="Upload a file to S3 and store metadata",
)

storage_router.add_api_route(
    "/{file_id}/download",
    download_file,
    methods=["GET"],
    summary="Download file",
    description="Stream file content from S3",
)

storage_router.add_api_route(
    "/{file_id}",
    get_file,
    methods=["GET"],
    summary="Get file",
    description="Get file metadata and a presigned URL for download",
)

storage_router.add_api_route(
    "/{file_id}",
    delete_file,
    methods=["DELETE"],
    summary="Delete file",
    description="Delete a file from S3 and remove metadata",
)
