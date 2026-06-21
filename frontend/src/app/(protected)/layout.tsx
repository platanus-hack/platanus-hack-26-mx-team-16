import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Fragment, type ReactNode } from "react";

import { COOKIE_REFRESH_TOKEN } from "@/src/constants";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";
import { SessionSync } from "@/src/presentation/common/session-sync";
import { StoreInitializer } from "@/src/presentation/common/store-initializer";

export const dynamic = "force-dynamic";

const authRepository = new HttpAuthRepository(serverHttp);

async function refreshServerSession() {
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

interface ProtectedLayoutProps {
  children: ReactNode;
}

export default async function ProtectedLayout({
  children,
}: ProtectedLayoutProps) {
  const session = await refreshServerSession();

  if (!session) {
    // Login moved off `/` (now the Hall of Shame) to `/login`.
    redirect("/login");
  }

  if (!session.tenant) {
    redirect("/unassigned");
  }

  // Keying the subtree by tenant slug forces a full remount of every page
  // (and its client stores' useEffect hooks) whenever the active tenant
  // changes server-side. Without this, router.refresh() would only re-run
  // Server Components, leaving client-side data fetched from the old tenant.
  return (
    <Fragment key={session.tenant.slug}>
      <SessionSync
        session={{
          user: session.user,
          tenant: session.tenant,
          tenantRole: session.tenantRole,
        }}
        accessToken={session.session.accessToken}
      />
      <StoreInitializer />
      {children}
    </Fragment>
  );
}
