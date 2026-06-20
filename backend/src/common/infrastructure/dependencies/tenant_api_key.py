"""FastAPI dependency: resolve a tenant from a ``dxk_`` M2M API key (F9 · M4).

Coexists with the JWT/`X-Tenant` path — M2M endpoints under ``/v1`` depend on this
instead of ``get_required_tenant`` + ``AuthenticatedUserDep``. Reads ``X-Api-Key``,
hashes it, looks up the tenant binding.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security.api_key import APIKeyHeader

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep, DomainContextDep
from src.tenants.application.api_keys.service import resolve_tenant_api_key
from src.tenants.domain.exceptions.api_keys import InvalidTenantApiKeyError
from src.tenants.infrastructure.repositories.sql_tenant_api_key import (
    SQLTenantApiKeyRepository,
)

_m2m_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)


async def get_tenant_from_api_key(
    session: AsyncSessionDep,
    domain: DomainContextDep,
    api_key: str = Security(_m2m_api_key_header),
) -> Tenant:
    # `now` activa la validación de expiración — sin él, una key expirada
    # seguiría autenticando (gap detectado en el recon E1).
    key = await resolve_tenant_api_key(
        api_key,
        SQLTenantApiKeyRepository(session),
        now=datetime.now(UTC),
    )
    if key is None:
        raise InvalidTenantApiKeyError
    tenant = await domain.tenant_repository.find(key.tenant_id)
    if tenant is None:
        raise InvalidTenantApiKeyError
    return tenant


M2MTenantDep = Annotated[Tenant, Depends(get_tenant_from_api_key)]
