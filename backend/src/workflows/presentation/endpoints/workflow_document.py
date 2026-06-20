"""Workflow document CRUD endpoints — UseCase + Presenter pattern."""

from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import (
    EventPublisherDep,
    get_app_context,
)
from src.common.infrastructure.dependencies.tenant import get_required_tenant, get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.workflow_documents.creator import (
    WorkflowDocumentCreator,
)
from src.workflows.application.workflow_documents.deleter import (
    WorkflowDocumentDeleter,
)
from src.workflows.application.workflow_documents.lister import (
    WorkflowDocumentLister,
)
from src.workflows.application.workflow_documents.updater import (
    WorkflowDocumentUpdater,
)
from src.workflows.presentation.presenters.workflow_document import (
    WorkflowDocumentPresenter,
)
from src.workflows.presentation.schemas.workflow_document import (
    UpdateWorkflowDocumentRequest,
    UploadWorkflowDocumentRequest,
)

# --- Workflow-level documents ------------------------------------------------


async def create_workflow_document(
    workflow_id: UUID,
    request: UploadWorkflowDocumentRequest,
    event_publisher: EventPublisherDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    document = await WorkflowDocumentCreator(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        case_id=request.case_id,
        file_id=request.file_id,
        file_name=request.file_name,
        document_type_id=request.document_type_id,
        document_repository=app_context.domain.document_repository,
        event_publisher=event_publisher,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowDocumentPresenter(instance=document).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def update_workflow_document(
    workflow_id: UUID,  # noqa: ARG001
    document_id: UUID,
    request: UpdateWorkflowDocumentRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    document = await WorkflowDocumentUpdater(
        document_id=document_id,
        tenant_id=tenant.uuid,
        document_repository=app_context.domain.document_repository,
        file_name=request.file_name,
        extraction=request.extraction,
        validation=request.validation,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowDocumentPresenter(instance=document).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def delete_workflow_document(
    workflow_id: UUID,  # noqa: ARG001
    document_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.delete])
    await WorkflowDocumentDeleter(
        document_id=document_id,
        tenant_id=tenant.uuid,
        document_repository=app_context.domain.document_repository,
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )


# --- Case-level documents ----------------------------------------------------


async def list_case_documents(
    workflow_id: UUID,  # noqa: ARG001
    case_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    documents = await WorkflowDocumentLister(
        case_id=case_id,
        tenant_id=tenant.uuid,
        document_repository=app_context.domain.document_repository,
    ).execute()
    return ApiJSONResponse(
        content=[WorkflowDocumentPresenter(instance=d).to_dict for d in documents],
        status_code=status.HTTP_200_OK,
    )


async def create_case_document(
    workflow_id: UUID,
    case_id: UUID,
    request: UploadWorkflowDocumentRequest,
    event_publisher: EventPublisherDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    document = await WorkflowDocumentCreator(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        case_id=case_id,
        file_id=request.file_id,
        file_name=request.file_name,
        document_type_id=request.document_type_id,
        document_repository=app_context.domain.document_repository,
        event_publisher=event_publisher,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowDocumentPresenter(instance=document).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def update_case_document(
    workflow_id: UUID,  # noqa: ARG001
    case_id: UUID,  # noqa: ARG001
    document_id: UUID,
    request: UpdateWorkflowDocumentRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    document = await WorkflowDocumentUpdater(
        document_id=document_id,
        tenant_id=tenant.uuid,
        document_repository=app_context.domain.document_repository,
        file_name=request.file_name,
        extraction=request.extraction,
        validation=request.validation,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowDocumentPresenter(instance=document).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def delete_case_document(
    workflow_id: UUID,  # noqa: ARG001
    case_id: UUID,  # noqa: ARG001
    document_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.delete])
    await WorkflowDocumentDeleter(
        document_id=document_id,
        tenant_id=tenant.uuid,
        document_repository=app_context.domain.document_repository,
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
