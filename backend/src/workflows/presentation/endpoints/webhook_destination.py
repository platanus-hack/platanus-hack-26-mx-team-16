"""Per-workflow webhook destination endpoints (spec connections §4.3 / §10).

Destinations are configured under a workflow; viewing requires
``WorkflowPermission.view`` and mutations require ``WorkflowPermission.update``.
Deliveries are surfaced via the per-destination events (delivery-log) endpoint.
"""

from uuid import UUID

from fastapi import Depends, Query, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.webhook_destinations.use_cases import (
    CreateWebhookDestination,
    DeleteWebhookDestination,
    GetWebhookDestination,
    ListWebhookDestinationEvents,
    ListWebhookDestinations,
    RegenerateWebhookDestinationSecret,
    UpdateWebhookDestination,
)
from src.workflows.presentation.presenters.webhook_destination import WebhookDestinationPresenter
from src.workflows.presentation.presenters.workflow_event import WorkflowEventPresenter
from src.workflows.presentation.schemas.webhook_destination import (
    CreateWebhookDestinationRequest,
    UpdateWebhookDestinationRequest,
)


async def list_webhook_destinations(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    destinations = await ListWebhookDestinations(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(
        content=[WebhookDestinationPresenter(instance=d).to_dict for d in destinations],
        status_code=status.HTTP_200_OK,
    )


async def create_webhook_destination(
    workflow_id: UUID,
    request: CreateWebhookDestinationRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    destination = await CreateWebhookDestination(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        name=request.name,
        url=request.url,
        description=request.description,
        enabled=request.enabled,
        subscribed_events=request.subscribed_events,
        secret=request.secret,
        api_version=request.api_version,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(
        content=WebhookDestinationPresenter(instance=destination).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def get_webhook_destination(
    workflow_id: UUID,
    destination_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    destination = await GetWebhookDestination(
        workflow_id=workflow_id,
        destination_id=destination_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(
        content=WebhookDestinationPresenter(instance=destination).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def update_webhook_destination(
    workflow_id: UUID,
    destination_id: UUID,
    request: UpdateWebhookDestinationRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    destination = await UpdateWebhookDestination(
        workflow_id=workflow_id,
        destination_id=destination_id,
        tenant_id=tenant.uuid,
        name=request.name,
        url=request.url,
        description=request.description,
        enabled=request.enabled,
        subscribed_events=request.subscribed_events,
        secret=request.secret,
        api_version=request.api_version,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(
        content=WebhookDestinationPresenter(instance=destination).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def delete_webhook_destination(
    workflow_id: UUID,
    destination_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    await DeleteWebhookDestination(
        workflow_id=workflow_id,
        destination_id=destination_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(content={"deleted": True}, status_code=status.HTTP_200_OK)


async def regenerate_webhook_destination_secret(
    workflow_id: UUID,
    destination_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    destination = await RegenerateWebhookDestinationSecret(
        workflow_id=workflow_id,
        destination_id=destination_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(
        content=WebhookDestinationPresenter(instance=destination).secret_dict,
        status_code=status.HTTP_200_OK,
    )


async def reveal_webhook_destination_secret(
    workflow_id: UUID,
    destination_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    # Reveals the stored signing secret so the detail UI can show/copy it on
    # demand (Stripe-style "click to reveal"). Same access bar as viewing the
    # destination; the secret is only sent on this explicit request, never in
    # the list/detail payloads.
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    destination = await GetWebhookDestination(
        workflow_id=workflow_id,
        destination_id=destination_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    return ApiJSONResponse(
        content=WebhookDestinationPresenter(instance=destination).secret_dict,
        status_code=status.HTTP_200_OK,
    )


async def list_webhook_destination_events(
    workflow_id: UUID,
    destination_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    delivery_status: str | None = Query(default=None, alias="deliveryStatus"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    # Validates the destination exists and belongs to this workflow (404 otherwise).
    await GetWebhookDestination(
        workflow_id=workflow_id,
        destination_id=destination_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.webhook_destination_repository,
    ).execute()
    events = await ListWebhookDestinationEvents(
        destination_id=destination_id,
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
