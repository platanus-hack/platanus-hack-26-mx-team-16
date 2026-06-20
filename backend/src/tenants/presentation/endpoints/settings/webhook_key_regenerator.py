from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_settings import TenantSettingPermission
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.tenant.webhook_key_regenerator import WebhookKeyRegenerator
from src.tenants.presentation.presenters.tenant_settings import TenantSettingsPresenter


async def regenerate_webhook_key(
    tenant_id: UUID,
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContextDep = None,
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantSettingPermission.update])

    tenant = await WebhookKeyRegenerator(
        tenant_id=tenant_id,
        tenant_repository=domain_context.tenant_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantSettingsPresenter(tenant).to_dict,
        status_code=status.HTTP_200_OK,
    )
