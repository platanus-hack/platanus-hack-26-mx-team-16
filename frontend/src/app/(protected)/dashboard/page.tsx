"use client";

import type { LucideIcon } from "lucide-react";
import { FileText, FolderOpen, TrendingUp, Zap } from "lucide-react";
import { useTranslations } from "next-intl";

import { useDashboardOverview } from "@/src/application/hooks/queries/dashboard";
import { useDashboardEvents } from "@/src/application/hooks/use-dashboard-events";
import type {
  OverviewSummary,
  QueueDelta,
  StatDelta,
} from "@/src/domain/entities/dashboard/overview";
import { AppShell } from "@/src/presentation/common/app-shell";
import { PermissionGuard } from "@/src/presentation/common/permission-guard";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import { Spinner } from "@/src/presentation/components/ui/spinner";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import { OverviewChart } from "@/src/presentation/dashboard/overview-chart";
import { ProcessingTab } from "@/src/presentation/dashboard/processing-tab";
import { RecentDocuments } from "@/src/presentation/dashboard/recent-documents";
import { StatCard } from "@/src/presentation/dashboard/stat-card";

const numberFormatter = new Intl.NumberFormat("en-US");

export default function DashboardPage() {
  const t = useTranslations("Dashboard");

  // Mount the SSE invalidation bus once for the whole page. The hook
  // pauses cleanly on unmount via its AbortController.
  useDashboardEvents();

  return (
    <PermissionGuard permission="dashboard.view">
      <AppShell
        activePath="/dashboard"
        breadcrumbItems={[{ label: t("title") }]}
      >
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{t("title")}</h2>
            <p className="text-muted-foreground">{t("description")}</p>
          </div>

          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList>
              <TabsTrigger value="overview">{t("tabs.overview")}</TabsTrigger>
              <TabsTrigger value="processing">
                {t("tabs.processing")}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              <OverviewTab />
            </TabsContent>

            <TabsContent value="processing" className="space-y-4">
              <ProcessingTab />
            </TabsContent>
          </Tabs>
        </div>
      </AppShell>
    </PermissionGuard>
  );
}

function OverviewTab() {
  const t = useTranslations("Dashboard");
  const { data, isLoading, isError } = useDashboardOverview();

  if (isLoading && !data) return <OverviewSkeleton />;
  if (isError || !data) return <OverviewError />;

  return (
    <>
      <OverviewStatCards summary={data.summary} />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>{t("throughput.title")}</CardTitle>
            <CardDescription>{t("throughput.description")}</CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            <OverviewChart data={data.throughput} />
          </CardContent>
        </Card>

        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>{t("recentDocuments.title")}</CardTitle>
            <CardDescription>
              {t("recentDocuments.description", {
                count: data.summary.documentsProcessed.value,
              })}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RecentDocuments documents={data.recentDocuments} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function OverviewStatCards({ summary }: { summary: OverviewSummary }) {
  const t = useTranslations("Dashboard.stats");
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <OverviewStat
        title={t("totalDocuments")}
        stat={summary.totalDocuments}
        icon={FileText}
      />
      <OverviewStat
        title={t("documentsProcessed")}
        stat={summary.documentsProcessed}
        icon={TrendingUp}
      />
      <OverviewStat
        title={t("activeWorkflows")}
        stat={summary.activeWorkflows}
        icon={FolderOpen}
      />
      <QueueStat
        title={t("processingQueue")}
        stat={summary.processingQueue}
        icon={Zap}
      />
    </div>
  );
}

function OverviewStat({
  title,
  stat,
  icon,
}: {
  title: string;
  stat: StatDelta;
  icon: LucideIcon;
}) {
  const t = useTranslations("Dashboard.deltaPct");
  const change =
    stat.deltaPct === null
      ? t("noData")
      : t("withSign", {
          sign: stat.deltaPct >= 0 ? "+" : "",
          value: stat.deltaPct.toFixed(1),
        });

  return (
    <StatCard
      title={title}
      value={numberFormatter.format(stat.value)}
      change={change}
      icon={icon}
    />
  );
}

function QueueStat({
  title,
  stat,
  icon,
}: {
  title: string;
  stat: QueueDelta;
  icon: LucideIcon;
}) {
  const t = useTranslations("Dashboard.hourlyDelta");
  const delta = stat.deltaSinceLastHour;
  const change =
    delta === null
      ? "—"
      : t("withSign", {
          sign: delta >= 0 ? "+" : "",
          value: numberFormatter.format(delta),
        });

  return (
    <StatCard
      title={title}
      value={numberFormatter.format(stat.value)}
      change={change}
      icon={icon}
    />
  );
}

function OverviewSkeleton() {
  return (
    <div className="flex items-center justify-center py-16">
      <Spinner size="md" variant="muted" />
    </div>
  );
}

function OverviewError() {
  const t = useTranslations("Dashboard.errors");
  return (
    <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
      {t("load")}
    </div>
  );
}
