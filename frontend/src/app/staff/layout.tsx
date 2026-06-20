import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Fragment, type ReactNode } from "react";

import { COOKIE_REFRESH_TOKEN } from "@/src/constants";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { serverHttp } from "@/src/infrastructure/http/client";
import { HttpAuthRepository } from "@/src/infrastructure/repositories/http-auth";
import { SessionSync } from "@/src/presentation/common/session-sync";
import { StaffShell } from "@/src/presentation/staff/staff-shell";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Consola staff · Doxiq",
};

const authRepository = new HttpAuthRepository(serverHttp);

/**
 * E5 · ADR 0001 — layout server de la consola staff.
 *
 * Gate por `user.isStaff` del payload de sesión (refresh server-side, el
 * mismo patrón del ProtectedLayout). El claim JWT `is_staff` solo gatea en
 * el backend (`StaffUserDep` re-consulta la fila activa por request); aquí
 * solo decidimos UI: sin sesión → "/", sesión sin staff → "/forbidden".
 *
 * Shell propio SIN selector de tenant: la consola es cross-tenant.
 */
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

export default async function StaffLayout({
  children,
}: {
  children: ReactNode;
}) {
  const session = await refreshServerSession();

  if (!session) {
    redirect("/");
  }

  if (!session.user.isStaff) {
    redirect("/forbidden");
  }

  return (
    <Fragment>
      <SessionSync
        session={{
          user: session.user,
          tenant: session.tenant ?? null,
          tenantRole: session.tenantRole ?? null,
        }}
        accessToken={session.session.accessToken}
      />
      <StaffShell>{children}</StaffShell>
    </Fragment>
  );
}
