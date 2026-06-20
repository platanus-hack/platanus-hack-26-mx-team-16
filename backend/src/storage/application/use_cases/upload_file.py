from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import UploadFile
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile as StarletteUploadFile

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.helpers.paths import safe_storage_key_name
from src.common.settings import settings
from src.common.domain.models.file_upload import Document
from src.common.domain.exceptions.storage import (
    FileTooLargeError,
    FileUploadError,
    UnsupportedMimeError,
)
from src.storage.domain.repositories.file_repository import FileRepository
from src.storage.infrastructure.s3_client import get_s3_client


def bytes_to_upload_file(content: bytes, filename: str, content_type: str) -> UploadFile:
    """Wrap in-memory bytes as an ``UploadFile`` (E6 · W5 bytes-first ingest).

    Native channels (email/WhatsApp) arrive with attachment bytes already in
    memory; this lets them reuse :class:`UploadFileUseCase` without a temp file.
    """
    return StarletteUploadFile(
        BytesIO(content),
        size=len(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@dataclass
class UploadFileUseCase(UseCase):
    tenant_id: UUID
    file: UploadFile
    file_repository: FileRepository
    # E6 · W5: MIMEs allowed ONLY for this call (channel context — voice notes).
    # The default keeps the web uploader restricted to ALLOWED_UPLOAD_MIMES.
    extra_allowed_mimes: list[str] = field(default_factory=list)

    async def execute(self) -> Document:
        file_id = uuid4()
        file_name = self.file.filename or "unnamed"
        mime = self.file.content_type or "application/octet-stream"

        allowed = [*settings.ALLOWED_UPLOAD_MIMES, *self.extra_allowed_mimes]
        if mime not in allowed:
            raise UnsupportedMimeError(mime=mime, allowed=allowed)

        contents = await self.file.read()
        size = len(contents)

        if size > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeError(size=size, max_size=settings.MAX_UPLOAD_SIZE)

        s3_key = f"{self.tenant_id}/{file_id}/{safe_storage_key_name(file_name)}"
        try:
            s3_client = get_s3_client()
            s3_client.put_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=s3_key,
                Body=contents,
                ContentType=mime,
            )
        except Exception as e:
            raise FileUploadError(str(e))

        now = datetime.now(UTC)
        file_upload = Document(
            uuid=file_id,
            tenant_id=self.tenant_id,
            file_name=file_name,
            mime=mime,
            size=size,
            s3_key=s3_key,
            created_at=now,
            updated_at=now,
        )
        return await self.file_repository.save(file_upload)
