"""Org-level connection account CRUD endpoints (spec connections §2.1/§3.2).

The whole org Connections registry is gated by the ``connections.manage``
permission (spec §9): credentials are sensitive, so only managers touch them.
"""

from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.connection import ConnectionPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.connections.application.use_cases.connection_account import (
    CreateConnectionAccount,
    DeleteConnectionAccount,
    GetConnectionAccount,
    ListConnectionAccounts,
    UpdateConnectionAccount,
)
from src.connections.presentation.presenters.connection_account import ConnectionAccountPresenter
from src.connections.presentation.schemas.connection_account import (
    CreateConnectionAccountRequest,
    UpdateConnectionAccountRequest,
)


async def list_connection_accounts(
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[ConnectionPermission.manage])
    accounts = await ListConnectionAccounts(
        tenant_id=tenant.uuid,
        repo=app_context.domain.connection_account_repository,
    ).execute()
    return ApiJSONResponse(
        content=[ConnectionAccountPresenter(instance=a).to_dict for a in accounts],
        status_code=status.HTTP_200_OK,
    )


async def create_connection_account(
    request: CreateConnectionAccountRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[ConnectionPermission.manage])
    account = await CreateConnectionAccount(
        tenant_id=tenant.uuid,
        provider=request.provider,
        display_name=request.display_name,
        capabilities=request.capabilities,
        config=request.config,
        secret=request.secret,
        repo=app_context.domain.connection_account_repository,
    ).execute()
    return ApiJSONResponse(
        content=ConnectionAccountPresenter(instance=account).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def get_connection_account(
    account_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[ConnectionPermission.manage])
    account = await GetConnectionAccount(
        account_id=account_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.connection_account_repository,
    ).execute()
    return ApiJSONResponse(
        content=ConnectionAccountPresenter(instance=account).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def update_connection_account(
    account_id: UUID,
    request: UpdateConnectionAccountRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[ConnectionPermission.manage])
    account = await UpdateConnectionAccount(
        account_id=account_id,
        tenant_id=tenant.uuid,
        display_name=request.display_name,
        capabilities=request.capabilities,
        status=request.status,
        config=request.config,
        secret=request.secret,
        repo=app_context.domain.connection_account_repository,
    ).execute()
    return ApiJSONResponse(
        content=ConnectionAccountPresenter(instance=account).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def delete_connection_account(
    account_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[ConnectionPermission.manage])
    await DeleteConnectionAccount(
        account_id=account_id,
        tenant_id=tenant.uuid,
        repo=app_context.domain.connection_account_repository,
    ).execute()
    return ApiJSONResponse(content={"deleted": True}, status_code=status.HTTP_200_OK)
