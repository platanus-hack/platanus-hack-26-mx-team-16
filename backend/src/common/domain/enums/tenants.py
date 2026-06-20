from src.common.domain.enums.base_enum import BaseEnum


class TenantRoleStatus(BaseEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class TenantStatus(BaseEnum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class TenantUserInvitationStatus(BaseEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class TenantBranchType(BaseEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class TenantBranchStatus(BaseEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class TenantPOSStatus(BaseEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"


class TenantBranchRole(BaseEnum):
    MANAGER = "MANAGER"
    STAFF = "STAFF"


class TenantBankAccountType(BaseEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"


class TenantAccountVendor(BaseEnum):
    TAKENOS = "TAKENOS"
    MERU = "MERU"
    WALLBIT = "WALLBIT"


class TenantBankAccountStatus(BaseEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class TenantPayoutStatus(BaseEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    WITHDRAWN = "WITHDRAWN"
