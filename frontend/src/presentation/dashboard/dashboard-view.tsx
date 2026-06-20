"use client";

import { ArrowRight, Building2, Shield, Users } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useSession } from "@/src/application/contexts/session";
import { useMembersQuery } from "@/src/application/hooks/queries/members";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";

/**
 * Generic post-login landing for the SaaS boilerplate. Shows a short
 * welcome plus a few read-only placeholder cards sourced from data that
 * already exists in any tenant: the member roster, the current user's
 * role, and the active workspace. Intentionally minimal — it is the
 * starting point each app is expected to flesh out.
 */
export function DashboardView() {
  const t = useTranslations("Dashboard");
  const { user, tenant, tenantRole } = useSession();
  const { data: members, isLoading: membersLoading } = useMembersQuery();

  const displayName = user?.firstName?.trim() || user?.username || "";
  const memberCount = members?.length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("welcome", { name: displayName })}
        </h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="size-4 text-primary" />
              {t("membersCardTitle")}
            </CardTitle>
            <CardDescription>{t("membersCardDescription")}</CardDescription>
          </CardHeader>
          <CardContent className="flex items-end justify-between gap-2">
            {membersLoading ? (
              <Skeleton className="h-9 w-12" />
            ) : (
              <span className="text-3xl font-semibold tabular-nums">
                {memberCount}
              </span>
            )}
            <Link
              href="/members"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              {t("membersLink")}
              <ArrowRight className="size-3" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="size-4 text-primary" />
              {t("roleCardTitle")}
            </CardTitle>
            <CardDescription>{t("roleCardDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <span className="text-lg font-medium">
              {tenantRole?.name ?? t("noRole")}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="size-4 text-primary" />
              {t("tenantCardTitle")}
            </CardTitle>
            <CardDescription>{t("tenantCardDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <span className="text-lg font-medium">
              {tenant?.name ?? t("noTenant")}
            </span>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("gettingStartedTitle")}</CardTitle>
          <CardDescription>{t("gettingStartedDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-primary" />
              {t("stepMembers")}
            </li>
            <li className="flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-primary" />
              {t("stepRoles")}
            </li>
            <li className="flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-primary" />
              {t("stepSettings")}
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
