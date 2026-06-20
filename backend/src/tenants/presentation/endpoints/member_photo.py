"""Upload a profile photo for a tenant member.

Uploads the raw file via the configured storage service, then writes the
resulting public URL to ``TenantUser.photo`` through the standard
``TenantUserUpdater`` use case. We don't go through the JSON PATCH
endpoint because that one is text-only — the photo itself needs to be
streamed as multipart.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from fastapi import Depends, File, UploadFile, status

from src.common.domain.entities.common.in_memory_file import InMemoryFile
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_user import TenantUserPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.assets.infrastructure.helpers.storage_url import build_storage_url
from src.tenants.presentation.presenters.tenant_user import TenantUserPresenter
from src.users.application.use_cases.tenant_user.updater import TenantUserUpdater


async def update_member_photo(
    tenant_user_id: UUID,
    photo: UploadFile = File(...),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    app_context: AppContext = Depends(get_app_context),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantUserPermission.update])

    file_bytes = await photo.read()
    await photo.close()

    in_memory = InMemoryFile(
        file_path=photo.filename or "photo",
        file_bytes=file_bytes,
    )
    storage_path = _build_photo_path(
        tenant_slug=_tenant_slug(current_tenant_user),
        tenant_user_id=tenant_user_id,
        file_name=in_memory.file_name or "photo",
    )
    uploaded = app_context.domain.storage_service.upload_file(replace(in_memory, file_path=storage_path))
    photo_url = build_storage_url(uploaded.file_path)

    updated_tenant_user = await TenantUserUpdater(
        tenant_id=current_tenant_user.tenant.uuid,
        tenant_user_id=tenant_user_id,
        payload={"photo": photo_url},
        query_bus=app_context.bus.query_bus,
        command_bus=app_context.bus.command_bus,
        phone_number_repository=app_context.domain.phone_repository,
        email_repository=app_context.domain.email_repository,
    ).execute()

    return ApiJSONResponse(
        content=TenantUserPresenter(updated_tenant_user).to_dict,
        status_code=status.HTTP_200_OK,
    )


def _tenant_slug(tenant_user: TenantUser) -> str:
    if tenant_user.tenant and tenant_user.tenant.slug:
        return tenant_user.tenant.slug
    return str(tenant_user.tenant.uuid) if tenant_user.tenant else "unknown"


def _build_photo_path(tenant_slug: str, tenant_user_id: UUID, file_name: str) -> str:
    return f"tenants/{tenant_slug}/members/{tenant_user_id}/{file_name}"
