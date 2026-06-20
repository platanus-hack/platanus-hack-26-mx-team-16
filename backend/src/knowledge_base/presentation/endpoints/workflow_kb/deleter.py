from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.knowledge_base.application.use_cases.delete_kb_document import DeleteKBDocument
from src.knowledge_base.infrastructure.repositories.sql_kb_document_repository import SQLKBDocumentRepository
from src.knowledge_base.infrastructure.repositories.sql_kb_embedding_repository import SQLKBEmbeddingRepository


async def delete_kb_document(
    workflow_id: UUID,
    document_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    await DeleteKBDocument(
        document_id=document_id,
        tenant_id=tenant.uuid,
        document_repository=SQLKBDocumentRepository(session),
        embedding_repository=SQLKBEmbeddingRepository(session),
    ).execute()

    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
