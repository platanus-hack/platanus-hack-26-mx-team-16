from uuid import UUID

from fastapi import Depends, File, Form, UploadFile, status
from pydantic import BaseModel, Field

from src.common.domain.contexts.domain import DomainContext
from src.common.domain.entities.common.in_memory_file import InMemoryFile
from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.currencies import CurrencyCode
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.tenant_settings import TenantSettingPermission
from src.common.infrastructure.dependencies.common import (
    BusContextDep,
    DomainContextDep,
    get_domain_context,
)
from src.common.infrastructure.dependencies.session import AuthenticatedUserDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.tenants.application.use_cases.tenant.registerer import TenantRegisterer
from src.tenants.application.use_cases.tenant.updater import TenantUpdater


class RegisterTenantRequest(BaseModel):
    name: str
    country_code: CountryIsoCode = Field(default=CountryIsoCode.MEXICO)


async def register_tenant(
    request: RegisterTenantRequest,
    domain_context: DomainContextDep,
    bus_context: BusContextDep,
    current_user: AuthenticatedUserDep,
) -> ApiJSONResponse:
    tenant = await TenantRegisterer(
        name=request.name,
        owner=current_user,
        country_code=request.country_code,
        tenant_repository=domain_context.tenant_repository,
        tenant_role_repository=domain_context.tenant_role_repository,
        command_bus=bus_context.command_bus,
        user_repository=domain_context.user_repository,
        tenant_user_repository=domain_context.tenant_user_repository,
    ).execute()

    return ApiJSONResponse(
        content=tenant.model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


class UpdateTenantRequest(CamelCaseRequest):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    country_code: CountryIsoCode | None = Field(default=None)
    currency_code: CurrencyCode | None = Field(default=None)

    @classmethod
    def as_form(
        cls,
        name: str | None = Form(default=None, min_length=1, max_length=150),
        country_code: CountryIsoCode | None = Form(default=None),
        currency_code: CurrencyCode | None = Form(default=None),
    ) -> "UpdateTenantRequest":
        return cls(
            name=name,
            country_code=country_code,
            currency_code=currency_code,
        )


async def update_tenant(
    tenant_id: UUID,
    request: UpdateTenantRequest = Depends(UpdateTenantRequest.as_form),
    logo: UploadFile | None = File(default=None),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    domain_context: DomainContext = Depends(get_domain_context),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[TenantSettingPermission.update])

    payload = request.model_dump(exclude_none=True, exclude_unset=True)
    logo_upload, logo_content_type = await _process_uploaded_logo(logo)

    tenant = await TenantUpdater(
        tenant_id=tenant_id,
        payload=payload,
        tenant_repository=domain_context.tenant_repository,
        storage_service=domain_context.storage_service,
        logo=logo_upload,
        logo_content_type=logo_content_type,
    ).execute()

    return ApiJSONResponse(
        content=tenant.model_dump(),
        status_code=status.HTTP_200_OK,
    )


async def _process_uploaded_logo(logo: UploadFile | None) -> tuple[InMemoryFile | None, str | None]:
    logo_upload: InMemoryFile | None = None
    logo_content_type: str | None = None

    if logo is not None:
        file_bytes = await logo.read()
        await logo.close()

        logo_content_type = logo.content_type or ""

        logo_upload = InMemoryFile(
            file_path=logo.filename or "tenant_logo",
            file_bytes=file_bytes,
        )

    return logo_upload, logo_content_type
