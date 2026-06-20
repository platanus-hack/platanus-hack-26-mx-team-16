"""Workflow case CRUD endpoints — UseCase + Presenter pattern."""

from uuid import UUID

from fastapi import Depends, status
from pydantic import BaseModel

from src.common.application.logging import get_logger
from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import TemporalClientDep, get_app_context
from src.common.infrastructure.dependencies.session import OptionalAuthenticatedUserDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant, get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.settings import settings
from src.workflows.application.workflow_cases.case_run_starter import EnsureCaseRunStarted
from src.workflows.application.workflow_cases.completeness import EvaluateCaseCompleteness
from src.workflows.application.workflow_cases.creator import WorkflowCaseCreator
from src.workflows.application.workflow_cases.deleter import WorkflowCaseDeleter
from src.workflows.application.workflow_cases.detail_getter import WorkflowCaseGetter
from src.workflows.application.workflow_cases.lister import WorkflowCaseLister
from src.workflows.application.workflow_cases.ready import RequestCaseReady
from src.workflows.application.workflow_cases.updater import WorkflowCaseUpdater
from src.workflows.domain.filters.workflow_case import WorkflowCaseFilters
from src.workflows.presentation.presenters.workflow_case import (
    WorkflowCaseDetailPresenter,
    WorkflowCasePresenter,
)
from src.workflows.presentation.schemas.workflow_case import (
    CreateWorkflowCaseRequest,
    UpdateWorkflowCaseRequest,
)

logger = get_logger(__name__)


class ReadyWorkflowCaseRequest(BaseModel):
    force: bool = False


async def list_cases(
    workflow_id: UUID,
    filters: WorkflowCaseFilters = Depends(),
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])

    page = await WorkflowCaseLister(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        filters=filters,
        case_repository=app_context.domain.workflow_case_repository,
        document_repository=app_context.domain.document_repository,
        processing_job_repository=app_context.domain.processing_job_repository,
    ).execute()

    presented_page = Page(
        next_cursor=page.next_cursor,
        items=[
            WorkflowCasePresenter(
                instance=item.case,
                documents=item.documents,
                has_failed_runs=item.has_failed_runs,
            ).to_dict
            for item in page.items or []
        ],
        limit=page.limit,
    )
    return ApiJSONResponse(content=presented_page, status_code=status.HTTP_200_OK)


async def create_case(
    workflow_id: UUID,
    request: CreateWorkflowCaseRequest,
    user: OptionalAuthenticatedUserDep,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.create])
    view = await WorkflowCaseCreator(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        name=request.name,
        case_repository=app_context.domain.workflow_case_repository,
        workflow_repository=app_context.domain.workflow_repository,
        document_repository=app_context.domain.document_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        created_by=user.uuid if user else None,
    ).execute()
    # E4 · diseño §3: si la receta del workflow espera documentos, el caso
    # arranca su run CASE# desde el nacimiento (best-effort).
    try:
        await EnsureCaseRunStarted(
            tenant_id=tenant.uuid,
            case_id=view.case.uuid,
            case_repository=app_context.domain.workflow_case_repository,
            pipeline_repository=app_context.domain.pipeline_repository,
            workflow_repository=app_context.domain.workflow_repository,
            temporal_client=temporal_client,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
        ).execute()
    except Exception:  # noqa: BLE001 — jamás rompe la creación
        logger.exception("case.case_run_start_failed", case_id=str(view.case.uuid))
    return ApiJSONResponse(
        content=WorkflowCasePresenter(instance=view.case, documents=view.documents).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def get_case(
    workflow_id: UUID,
    case_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    view = await WorkflowCaseGetter(
        case_id=case_id,
        tenant_id=tenant.uuid,
        case_repository=app_context.domain.workflow_case_repository,
        document_repository=app_context.domain.document_repository,
        document_type_repository=app_context.domain.document_type_repository,
        case_event_repository=app_context.domain.case_event_repository,
        workflow_id=workflow_id,
    ).execute()

    return ApiJSONResponse(
        content=WorkflowCaseDetailPresenter(
            instance=view.case,
            document_groups=view.document_groups,
            timeline=view.timeline,
            children_by_status=view.children_by_status,
        ).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def update_case(
    workflow_id: UUID,
    case_id: UUID,
    request: UpdateWorkflowCaseRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    view = await WorkflowCaseUpdater(
        case_id=case_id,
        tenant_id=tenant.uuid,
        case_repository=app_context.domain.workflow_case_repository,
        document_repository=app_context.domain.document_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        name=request.name,
        status=request.status,
        case_event_repository=app_context.domain.case_event_repository,
        actor=str(current_tenant_user.user_id) if current_tenant_user else None,
        workflow_id=workflow_id,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowCasePresenter(instance=view.case, documents=view.documents).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def get_case_completeness(
    workflow_id: UUID,
    case_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    """Cálculo fresco de completitud (E4) — misma semántica que el M2M."""
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    result = await EvaluateCaseCompleteness(
        tenant_id=tenant.uuid,
        case_id=case_id,
        case_repository=app_context.domain.workflow_case_repository,
        document_repository=app_context.domain.document_repository,
        document_type_repository=app_context.domain.document_type_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        workflow_repository=app_context.domain.workflow_repository,
        persist=False,
        workflow_id=workflow_id,
    ).execute()
    return ApiJSONResponse(
        content={
            "satisfied": result.satisfied,
            "autoReady": result.auto_ready,
            "readyAt": result.case.ready_at.isoformat() if result.case.ready_at else None,
            "required": result.snapshot.get("required") or {},
            "present": result.snapshot.get("present") or {},
            "missing": result.snapshot.get("missing") or [],
        },
        status_code=status.HTTP_200_OK,
    )


async def ready_case(
    workflow_id: UUID,
    case_id: UUID,
    request: ReadyWorkflowCaseRequest,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    """Marcar listo (E4): idempotente; 409 ``case.not_complete`` sin force."""
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    result = await RequestCaseReady(
        tenant_id=tenant.uuid,
        case_id=case_id,
        case_repository=app_context.domain.workflow_case_repository,
        document_repository=app_context.domain.document_repository,
        document_type_repository=app_context.domain.document_type_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        workflow_repository=app_context.domain.workflow_repository,
        temporal_client=temporal_client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        force=request.force,
        workflow_id=workflow_id,
    ).execute()
    return ApiJSONResponse(
        content={
            "caseId": str(case_id),
            "outcome": result.outcome,
            "readyAt": result.case.ready_at.isoformat() if result.case.ready_at else None,
        },
        status_code=status.HTTP_200_OK,
    )


async def delete_case(
    workflow_id: UUID,
    case_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.delete])
    await WorkflowCaseDeleter(
        case_id=case_id,
        tenant_id=tenant.uuid,
        case_repository=app_context.domain.workflow_case_repository,
        workflow_id=workflow_id,
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
