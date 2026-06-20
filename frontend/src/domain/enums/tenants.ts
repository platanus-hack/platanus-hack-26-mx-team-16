export enum TenantRoleStatus {
  ACTIVE = "ACTIVE",
  INACTIVE = "INACTIVE",
}

export enum TenantStatus {
  ACTIVE = "ACTIVE",
  PENDING = "PENDING",
  INACTIVE = "INACTIVE",
  SUSPENDED = "SUSPENDED",
}

export enum TenantBranchType {
  PRIMARY = "primary",
  SECONDARY = "secondary",
}

export enum TenantBranchStatus {
  ACTIVE = "ACTIVE",
  INACTIVE = "INACTIVE",
  SUSPENDED = "SUSPENDED",
}

export enum TenantPOSStatus {
  ACTIVE = "ACTIVE",
  INACTIVE = "INACTIVE",
  MAINTENANCE = "MAINTENANCE",
  DECOMMISSIONED = "DECOMMISSIONED",
}

export enum TenantBranchRole {
  MANAGER = "MANAGER",
  STAFF = "STAFF",
}

export enum TenantBankAccountType {
  CHECKING = "checking",
  SAVINGS = "savings",
  BUSINESS = "business",
}

export enum TenantBankAccountStatus {
  ACTIVE = "active",
  INACTIVE = "inactive",
  SUSPENDED = "suspended",
}

export enum TenantBankAccountVendor {
  TAKENOS = "TAKENOS",
  MERU = "MERU",
  WALLBIT = "WALLBIT",
}

export enum TenantPayoutStatus {
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  WITHDRAWN = "WITHDRAWN",
}
