from dataclasses import dataclass
from typing import Any

from src.common.domain.contexts.client import ConsumerClient

# TODO: These modules need to be implemented or removed
# from src.common.domain.enums.locales import Language, TimeZone
# from src.common.domain.interfaces.locales import LocaleService
# from src.common.domain.models.country_config import CountryConfig
# from src.common.domain.models.tenant import Tenant
# from src.common.domain.models.tenant_customer import TenantCustomer
# from src.common.domain.models.tenant_user import TenantUser


@dataclass
class LocaleContext:
    time_zone: Any  # TimeZone - TODO: implement TimeZone enum
    language: Any  # Language - TODO: implement Language enum
    country_config: Any  # CountryConfig - TODO: implement CountryConfig model
    locale_service: Any | None = None  # LocaleService - TODO: implement LocaleService interface
    client: ConsumerClient | None = None


@dataclass
class TenantContext:
    tenant: Any | None = None  # Tenant - TODO: implement Tenant model
    tenant_user: Any | None = None  # TenantUser - TODO: implement TenantUser model
    tenant_customer: Any | None = None  # TenantCustomer - TODO: implement TenantCustomer model
