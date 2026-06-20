"""Knowledge Base search and rule suggestion endpoints."""

from fastapi import Depends

from src.common.domain.constants import status
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.knowledge_base.application.use_cases.retrieve_kb_context import RetrieveKBContext
from src.knowledge_base.application.use_cases.suggest_rules import SuggestRules
from src.knowledge_base.infrastructure.repositories.sql_kb_embedding_repository import SQLKBEmbeddingRepository
from src.knowledge_base.infrastructure.services.embedder import Embedder
from src.knowledge_base.presentation.schemas.kb_schemas import SearchKBRequest, SuggestRulesRequest


async def search_chunks(
    request: SearchKBRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    chunks = await RetrieveKBContext(
        tenant_id=tenant.uuid,
        query=request.query,
        embedding_repository=SQLKBEmbeddingRepository(session),
        embedder=Embedder(),
        top_k=request.top_k,
        kb_document_ids=request.document_ids,
    ).execute()
    return ApiJSONResponse(
        content=[
            {
                "uuid": str(chunk.uuid),
                "document_id": str(chunk.kb_document_id),
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
            }
            for chunk in chunks
        ],
        status_code=status.HTTP_200_OK,
    )


async def suggest_rules(
    request: SuggestRulesRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    result = await SuggestRules(
        tenant_id=tenant.uuid,
        query=request.query,
        embedding_repository=SQLKBEmbeddingRepository(session),
        embedder=Embedder(),
        top_k=request.top_k,
        kb_document_ids=request.document_ids,
    ).execute()
    return ApiJSONResponse(
        content=result,
        status_code=status.HTTP_200_OK,
    )
