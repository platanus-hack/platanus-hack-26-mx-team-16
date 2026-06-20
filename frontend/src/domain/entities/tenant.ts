import { TenantStatus } from "@/src/domain/enums/tenants";

export interface Tenant {
  uuid: string;
  name: string;
  slug: string;
  timeZone: string;
  countryCode: string;
  currencyCode: string;
  currencySymbol: string;
  logoUrl?: string | null;
  status: TenantStatus;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export function isTenantActive(tenant: Tenant): boolean {
  return tenant.status === TenantStatus.ACTIVE;
}

export const emptyTenant: Tenant = {
  uuid: "",
  name: "",
  slug: "",
  timeZone: "",
  countryCode: "",
  currencyCode: "",
  currencySymbol: "",
  status: TenantStatus.ACTIVE,
};
