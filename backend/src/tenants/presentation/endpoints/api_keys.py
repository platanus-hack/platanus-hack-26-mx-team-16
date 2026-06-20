"""Tenant M2M API-key endpoints (F9). JWT-admin; mints `dxk_` keys for M2M use."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, status
from pydantic import BaseModel, Field

from src.common.domain.models.tenant_api_key import TenantApiKey
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.api_keys.service import MintTenantApiKey
from src.tenants.infrastructure.repositories.sql_tenant_api_key import (
    SQLTenantApiKeyRepository,
)


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


def _present(key: TenantApiKey) -> dict:
    return {
        "uuid": str(key.uuid),
        "name": key.name,
        "prefix": key.prefix,
        "enabled": key.enabled,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "created_at": key.created_at.isoformat() if key.created_at else None,
    }


async def create_api_key(
    request: CreateApiKeyRequest,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    minted = await MintTenantApiKey(
        tenant_id=tenant.uuid,
        name=request.name,
        repository=SQLTenantApiKeyRepository(session),
    ).execute()
    # The plaintext key is returned exactly once.
    return ApiJSONResponse(
        content={**_present(minted.key), "key": minted.plaintext},
        status_code=status.HTTP_201_CREATED,
    )


async def list_api_keys(
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    keys = await SQLTenantApiKeyRepository(session).list_by_tenant(tenant.uuid)
    return ApiJSONResponse(content=[_present(k) for k in keys], status_code=status.HTTP_200_OK)


async def revoke_api_key(
    key_id: UUID,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    await SQLTenantApiKeyRepository(session).revoke(key_id, tenant.uuid)
    return ApiJSONResponse(content={"revoked": True}, status_code=status.HTTP_200_OK)
