from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.knowledge_base.application.use_cases.list_kb_documents import ListKBDocuments
from src.knowledge_base.infrastructure.repositories.sql_kb_document_repository import SQLKBDocumentRepository
from src.knowledge_base.presentation.presenters.kb_document_presenter import KBDocumentPresenter


async def list_kb_documents(
    workflow_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    documents = await ListKBDocuments(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        document_repository=SQLKBDocumentRepository(session),
    ).execute()
    return ApiJSONResponse(
        content=[KBDocumentPresenter(instance=document).to_dict for document in documents],
        status_code=status.HTTP_200_OK,
    )
