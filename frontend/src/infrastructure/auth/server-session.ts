import { cookies } from "next/headers";

import { COOKIE_REFRESH_TOKEN } from "@/src/constants";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";

const authRepository = new HttpAuthRepository(serverHttp);

/**
 * Refreshes the session server-side from the refresh-token cookie and returns
 * the full `TenantUserSession` (session tokens + user + tenant + tenantRole),
 * or `null` when there is no valid session.
 *
 * Shared by the protected layout (gates the app) and the `/unassigned` page
 * (gates tenant onboarding) so both read the session through identical logic.
 */
export async function refreshServerSession() {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(COOKIE_REFRESH_TOKEN)?.value;

  if (!refreshToken) {
    return null;
  }

  const result = await authRepository.refresh(refreshToken);
  if (isErrorFeedback(result)) {
    return null;
  }

  return result.data;
}
