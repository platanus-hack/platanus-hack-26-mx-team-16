"""File storage CRUD endpoints."""

from urllib.parse import quote
from uuid import UUID

from fastapi import Depends, UploadFile, status
from fastapi.responses import StreamingResponse

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.storage.application.use_cases.delete_file import DeleteFile
from src.storage.application.use_cases.get_file import GetFile
from src.storage.application.use_cases.upload_file import UploadFileUseCase
from src.storage.infrastructure.repositories.s3_file_repository import S3FileRepository
from src.storage.infrastructure.s3_client import get_s3_client
from src.storage.presentation.presenters.file_upload import FileUploadPresenter


async def upload_file(
    file: UploadFile,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    file_upload = await UploadFileUseCase(
        tenant_id=tenant.uuid,
        file=file,
        file_repository=S3FileRepository(session),
    ).execute()
    return ApiJSONResponse(
        content=FileUploadPresenter(instance=file_upload).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def get_file(
    file_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    result = await GetFile(
        file_id=file_id,
        tenant_id=tenant.uuid,
        file_repository=S3FileRepository(session),
    ).execute()
    return ApiJSONResponse(
        content=FileUploadPresenter(
            instance=result["file"],
            presigned_url=result["presigned_url"],
        ).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def download_file(
    file_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> StreamingResponse:
    repo = S3FileRepository(session)
    result = await GetFile(
        file_id=file_id,
        tenant_id=tenant.uuid,
        file_repository=repo,
    ).execute()
    doc = result["file"]
    s3 = get_s3_client()
    from src.common.settings import settings

    s3_response = s3.get_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=doc.s3_key,
    )
    return StreamingResponse(
        content=s3_response["Body"],
        media_type=doc.mime,
        headers={
            "Content-Disposition": _content_disposition(doc.file_name),
        },
    )


def _content_disposition(file_name: str, disposition: str = "inline") -> str:
    """Build an RFC 6266 Content-Disposition value.

    HTTP headers must be latin-1 encodable, so non-ASCII file names (e.g.
    "Documentación.pdf") are emitted via the ``filename*=utf-8''`` parameter
    while keeping a plain ``filename=`` for clients that only understand it.
    """
    quoted = quote(file_name, safe="")
    if quoted == file_name:
        return f'{disposition}; filename="{file_name}"'
    ascii_fallback = file_name.encode("ascii", "ignore").decode("ascii")
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=utf-8''{quoted}"


async def delete_file(
    file_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    await DeleteFile(
        file_id=file_id,
        tenant_id=tenant.uuid,
        file_repository=S3FileRepository(session),
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
