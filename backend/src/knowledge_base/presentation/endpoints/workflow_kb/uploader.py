from uuid import UUID

from fastapi import Depends, Form, UploadFile, status

from src.common.application.commands.knowledge_base import VectorizeKBDocumentCommand
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep, BusContextDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.knowledge_base.application.use_cases.upload_kb_document import KBDocumentUploader
from src.knowledge_base.infrastructure.repositories.sql_kb_document_repository import SQLKBDocumentRepository
from src.knowledge_base.presentation.presenters.kb_document_presenter import KBDocumentPresenter


async def upload_kb_document(
    workflow_id: UUID,
    file: UploadFile,
    session: AsyncSessionDep,
    bus_context: BusContextDep,
    tenant: Tenant = Depends(get_required_tenant),
    slug: str | None = Form(default=None),
) -> ApiJSONResponse:
    file_content = await file.read()
    file_name = file.filename or "unknown"
    mime_type = file.content_type or "application/octet-stream"

    document = await KBDocumentUploader(
        tenant_id=tenant.uuid,
        file_name=file_name,
        mime_type=mime_type,
        workflow_id=workflow_id,
        slug=slug,
        document_repository=SQLKBDocumentRepository(session),
    ).execute()

    await bus_context.command_bus.dispatch(
        command=VectorizeKBDocumentCommand(
            document_id=document.uuid,
            tenant_id=tenant.uuid,
            file_name=file_name,
            mime_type=mime_type,
            file_content=file_content,
        ),
        run_async=True,
    )

    return ApiJSONResponse(
        content=KBDocumentPresenter(instance=document).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
