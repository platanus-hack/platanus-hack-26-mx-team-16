from src.common.domain.enums.base_enum import BaseEnum


class TenantUserStatus(BaseEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
