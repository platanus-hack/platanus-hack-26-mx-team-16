from src.common.database.models.tenants.tenant import TenantORM
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.currencies import CurrencyCode
from src.common.domain.enums.locales import TimeZone
from src.common.domain.enums.tenants import TenantStatus


def build_tenant(
    orm_instance: TenantORM,
) -> Tenant:
    return Tenant(
        uuid=orm_instance.uuid,
        name=orm_instance.name,
        slug=orm_instance.slug,
        status=TenantStatus.from_value(orm_instance.status),
        time_zone=TimeZone.from_value(orm_instance.time_zone),
        currency_code=CurrencyCode.from_value(orm_instance.currency_code),
        country_code=CountryIsoCode.from_value(orm_instance.country_code),
        owner_id=orm_instance.owner_id,
        logo_url=orm_instance.logo_url,
        is_deleted=orm_instance.is_deleted,
        webhook_signature_key=orm_instance.webhook_signature_key,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
