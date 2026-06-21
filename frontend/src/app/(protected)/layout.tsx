import { redirect } from "next/navigation";
import { Fragment, type ReactNode } from "react";

import { refreshServerSession } from "@/src/infrastructure/auth/server-session";
import { SessionSync } from "@/src/presentation/common/session-sync";
import { StoreInitializer } from "@/src/presentation/common/store-initializer";

export const dynamic = "force-dynamic";

interface ProtectedLayoutProps {
  children: ReactNode;
}

export default async function ProtectedLayout({
  children,
}: ProtectedLayoutProps) {
  const session = await refreshServerSession();

  if (!session) {
    // Login moved off `/` (now the leaderboard) to `/login`.
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
