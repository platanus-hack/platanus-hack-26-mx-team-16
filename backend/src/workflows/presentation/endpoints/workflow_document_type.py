"""Workflow-scoped document type endpoints — UseCase + Presenter pattern."""

from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.document_types.creator import DocumentTypeCreator
from src.workflows.application.document_types.deleter import DocumentTypeDeleter
from src.workflows.application.document_types.lister import DocumentTypeLister
from src.workflows.presentation.presenters.document_type import DocumentTypePresenter
from src.workflows.presentation.schemas.document_type import CreateDocumentTypeRequest


async def list_workflow_document_types(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    document_types = await DocumentTypeLister(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        document_type_repository=app_context.domain.document_type_repository,
    ).execute()

    return ApiJSONResponse(
        content=[DocumentTypePresenter(instance=dt).to_dict for dt in document_types],
        status_code=status.HTTP_200_OK,
    )


async def create_workflow_document_type(
    workflow_id: UUID,
    request: CreateDocumentTypeRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    document_type = await DocumentTypeCreator(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        name=request.name,
        description=request.description,
        is_shareable=request.is_shareable,
        fields=request.fields,
        validation_rules=request.validation_rules,
        document_type_repository=app_context.domain.document_type_repository,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()

    return ApiJSONResponse(
        content=DocumentTypePresenter(instance=document_type).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def delete_workflow_document_type(
    workflow_id: UUID,  # noqa: ARG001 — kept for URL symmetry
    document_type_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    await DocumentTypeDeleter(
        document_type_id=document_type_id,
        tenant_id=tenant.uuid,
        document_type_repository=app_context.domain.document_type_repository,
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
