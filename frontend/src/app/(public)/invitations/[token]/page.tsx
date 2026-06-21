import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { cache, Suspense } from "react";

import { Settings } from "@/src/settings";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";
import { AcceptInvitationForm } from "./accept-invitation-form";

interface InvitationView {
  email: string;
  tenantName: string;
  roleName: string | null;
  expiresAt: string | null;
  requiresPassword: boolean;
}

type LoadResult =
  | { kind: "ok"; data: InvitationView }
  | { kind: "not_found" }
  | { kind: "already_accepted" }
  | { kind: "expired" };

const loadInvitation = cache(async (token: string): Promise<LoadResult> => {
  try {
    const res = await fetch(
      `${Settings.apiBaseUrl}/v1/invitations/${encodeURIComponent(token)}`,
      { cache: "no-store" }
    );
    if (res.ok) {
      const body = await res.json();
      const data = body?.data as InvitationView | undefined;
      if (!data) return { kind: "not_found" };
      return { kind: "ok", data };
    }
    const body = (await res.json().catch(() => ({}))) as {
      errors?: { code?: string }[];
    };
    const code = body?.errors?.[0]?.code ?? "";
    if (code === "tenants.InvitationAlreadyAccepted") {
      return { kind: "already_accepted" };
    }
    if (code === "tenants.InvitationExpired") {
      return { kind: "expired" };
    }
    return { kind: "not_found" };
  } catch {
    return { kind: "not_found" };
  }
});

function CenteredCard({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6 rounded-lg border border-border bg-card p-8 shadow-sm">
        <div className="flex justify-center">
          <BrandLockup href="/" size="lg" owlState="idle" />
        </div>
        {children}
      </div>
    </main>
  );
}

function StateHeader({
  tag,
  title,
  body,
}: {
  tag: string;
  title: string;
  body: string;
}) {
  return (
    <header className="space-y-2 text-center">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {tag}
      </p>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="text-sm text-muted-foreground">{body}</p>
    </header>
  );
}

export default async function InvitationPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const t = await getTranslations("Invitations");
  const { token } = await params;
  const result = await loadInvitation(token);

  if (result.kind === "already_accepted") {
    return (
      <CenteredCard>
        <StateHeader
          tag={t("tag")}
          title={t("alreadyAcceptedTitle")}
          body={t("alreadyAcceptedBody")}
        />
        <Link
          href="/"
          className="inline-flex w-full items-center justify-center rounded-md bg-primary-action px-4 py-2 text-sm font-medium text-primary-action-foreground shadow-sm transition hover:bg-primary-action/90"
        >
          {t("goToLogin")}
        </Link>
      </CenteredCard>
    );
  }

  if (result.kind === "expired") {
    return (
      <CenteredCard>
        <StateHeader
          tag={t("tag")}
          title={t("expiredTitle")}
          body={t("expiredBody")}
        />
      </CenteredCard>
    );
  }

  if (result.kind === "not_found") {
    return (
      <CenteredCard>
        <StateHeader
          tag={t("tag")}
          title={t("notFoundTitle")}
          body={t("notFoundBody")}
        />
      </CenteredCard>
    );
  }

  const invitation = result.data;

  return (
    <CenteredCard>
      <header className="space-y-2 text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {t("tag")}
        </p>
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("invitedTo")}{" "}
          <span className="text-primary">{invitation.tenantName}</span>
        </h1>
        <p className="text-sm text-muted-foreground">
          {invitation.email}
          {invitation.roleName ? (
            <>
              <span className="mx-1.5">·</span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em]">
                {invitation.roleName}
              </span>
            </>
          ) : null}
        </p>
      </header>

      <Suspense>
        <AcceptInvitationForm
          token={token}
          requiresPassword={invitation.requiresPassword}
        />
      </Suspense>
    </CenteredCard>
  );
}
