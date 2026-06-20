"""Workflow webhook endpoints: secret regenerate + delivery log + replay (§4.9/§10)."""

from uuid import UUID

from fastapi import Depends, Query, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant, get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.workflows.webhook_event_lister import WorkflowEventsLister
from src.workflows.application.workflows.webhook_event_replayer import WorkflowEventReplayer
from src.workflows.application.workflows.webhook_secret_regenerator import (
    WorkflowWebhookSecretRegenerator,
)
from src.workflows.presentation.presenters.workflow_event import WorkflowEventPresenter


async def regenerate_workflow_webhook_secret(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    workflow = await WorkflowWebhookSecretRegenerator(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()
    # Secret is only exposed here (settings), never in the general workflow presenter (§4.9).
    return ApiJSONResponse(
        content={"webhook_secret": workflow.webhook_secret},
        status_code=status.HTTP_200_OK,
    )


async def list_workflow_events(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    delivery_status: str | None = Query(default=None, alias="deliveryStatus"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    events = await WorkflowEventsLister(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_event_repository=app_context.domain.workflow_event_repository,
        delivery_status=delivery_status,
        limit=limit,
        offset=offset,
    ).execute()
    return ApiJSONResponse(
        content=[WorkflowEventPresenter(instance=event).to_dict for event in events],
        status_code=status.HTTP_200_OK,
    )


async def replay_workflow_event(
    workflow_id: UUID,
    event_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    event = await WorkflowEventReplayer(
        workflow_id=workflow_id,
        event_uuid=event_id,
        tenant_id=tenant.uuid,
        workflow_event_repository=app_context.domain.workflow_event_repository,
        workflow_repository=app_context.domain.workflow_repository,
        webhook_destination_repository=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowEventPresenter(instance=event).detail_dict,
        status_code=status.HTTP_200_OK,
    )
