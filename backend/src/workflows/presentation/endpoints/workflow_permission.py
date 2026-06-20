"""Workflow permissions endpoints (workflow access type + explicit members).

Viewing requires ``WorkflowPermission.view``; mutations require
``WorkflowPermission.update``. Access to the workflow itself (and therefore to
these endpoints) is gated by the router-level ``verify_workflow_access`` guard.
"""

from uuid import UUID

from fastapi import Depends, status

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
from src.workflows.application.workflow_members.use_cases import (
    AddWorkflowMember,
    GetWorkflowPermissions,
    ListAssignableUsers,
    RemoveWorkflowMember,
    SetWorkflowAccessType,
    UpdateWorkflowMemberRole,
)
from src.workflows.presentation.presenters.workflow_member import (
    AssignableUserPresenter,
    WorkflowMemberPresenter,
    WorkflowPermissionsPresenter,
)
from src.workflows.presentation.schemas.workflow_member import (
    AddMemberRequest,
    SetAccessTypeRequest,
    UpdateMemberRoleRequest,
)


async def get_workflow_permissions(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    permissions = await GetWorkflowPermissions(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
        member_repository=app_context.domain.workflow_member_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowPermissionsPresenter(instance=permissions).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def update_workflow_access_type(
    workflow_id: UUID,
    request: SetAccessTypeRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    permissions = await SetWorkflowAccessType(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        access_type=request.access_type,
        workflow_repository=app_context.domain.workflow_repository,
        member_repository=app_context.domain.workflow_member_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowPermissionsPresenter(instance=permissions).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def add_workflow_member(
    workflow_id: UUID,
    request: AddMemberRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    member = await AddWorkflowMember(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        user_id=request.user_id,
        role=request.role,
        workflow_repository=app_context.domain.workflow_repository,
        member_repository=app_context.domain.workflow_member_repository,
        tenant_user_repository=app_context.domain.tenant_user_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowMemberPresenter(instance=member).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def update_workflow_member_role(
    workflow_id: UUID,
    user_id: UUID,
    request: UpdateMemberRoleRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    member = await UpdateWorkflowMemberRole(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        user_id=user_id,
        role=request.role,
        member_repository=app_context.domain.workflow_member_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowMemberPresenter(instance=member).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def remove_workflow_member(
    workflow_id: UUID,
    user_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    await RemoveWorkflowMember(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        user_id=user_id,
        member_repository=app_context.domain.workflow_member_repository,
    ).execute()
    return ApiJSONResponse(content={"deleted": True}, status_code=status.HTTP_200_OK)


async def list_assignable_users(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    users = await ListAssignableUsers(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        member_repository=app_context.domain.workflow_member_repository,
        tenant_user_repository=app_context.domain.tenant_user_repository,
    ).execute()
    return ApiJSONResponse(
        content=[AssignableUserPresenter(instance=u).to_dict for u in users],
        status_code=status.HTTP_200_OK,
    )
