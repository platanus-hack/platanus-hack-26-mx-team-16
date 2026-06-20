from typing import Annotated
from venv import logger

from fastapi import Depends, Header

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.exceptions.tenants import TenantNotFoundError
from src.common.domain.exceptions.users import TenantUserRequiredError
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import AuthenticatedUserDep


async def get_tenant(
    domaing_context: DomainContextDep,
    tenant_slug: Annotated[str | None, Header(alias="X-Tenant")] = None,
) -> Tenant | None:
    if not tenant_slug or not tenant_slug.strip():
        raise TenantNotFoundError

    return await domaing_context.tenant_repository.find_by_slug(slug=tenant_slug.strip())


TenantDep = Annotated[str | None, Depends(get_tenant)]


async def get_required_tenant(
    domaing_context: DomainContextDep,
    tenant_slug: Annotated[str | None, Header(alias="X-Tenant")] = None,
) -> Tenant:
    if not tenant_slug or not tenant_slug.strip():
        logger.error(f"TenantHeaderRequired: slug={tenant_slug}")
        raise TenantNotFoundError

    slug = tenant_slug.strip()
    tenant = await domaing_context.tenant_repository.find_by_slug(slug)
    if not tenant:
        logger.error(f"TenantNotFound: slug={tenant_slug}")
        raise TenantNotFoundError

    return tenant


RequiredTenantDep = Annotated[Tenant | None, Depends(get_required_tenant)]


async def get_tenant_user(
    user: AuthenticatedUserDep,
    domaing_context: DomainContextDep,
    tenant: RequiredTenantDep,
) -> TenantUser | None:
    return await domaing_context.tenant_user_repository.find_by_args(
        user_id=user.uuid,
        tenant_id=tenant.uuid,
    )


TenantUserDep = Annotated[str | None, Depends(get_tenant_user)]


async def get_required_tenant_user(
    user: AuthenticatedUserDep,
    domaing_context: DomainContextDep,
    tenant: RequiredTenantDep,
) -> TenantUser:
    tenant_user = await domaing_context.tenant_user_repository.find_by_args(
        user_id=user.uuid,
        tenant_id=tenant.uuid,
    )
    if not tenant_user:
        raise TenantUserRequiredError
    return tenant_user


RequiredTenantUserDep = Annotated[str | None, Depends(get_required_tenant_user)]
