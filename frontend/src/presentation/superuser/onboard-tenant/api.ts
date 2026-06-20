"use client";

import { authHttp } from "@/src/infrastructure/http/client";
import type { MemberRoleSlug } from "@/src/application/stores/onboard-tenant-wizard-store";

export interface OnboardTenantApiResponse {
  data: {
    tenant: {
      uuid: string;
      name: string;
      slug: string;
      timeZone: string;
      countryCode: string;
      currencyCode: string;
    };
    invitations: Array<{
      uuid: string;
      tenantId: string;
      email: string;
      tenantRoleId: string | null;
      token: string;
      status: string;
      expiresAt: string | null;
    }>;
  };
}

export interface OnboardTenantPayload {
  name: string;
  countryCode: string;
  industryId?: string | null;
  members: Array<{ email: string; roleSlug: MemberRoleSlug }>;
  skipEmail: boolean;
}

export async function onboardTenant(
  payload: OnboardTenantPayload,
): Promise<OnboardTenantApiResponse["data"]> {
  const res = await authHttp.post<OnboardTenantApiResponse>(
    "/v1/tenants/onboard",
    payload,
  );
  return res.data.data;
}
