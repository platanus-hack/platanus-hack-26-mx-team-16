"use client";

import {
  Check,
  Copy,
  Eye,
  Inbox,
  Pencil,
  RefreshCw,
  Trash2,
  Webhook,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  useDeleteWebhookDestinationMutation,
  useRegenerateWebhookDestinationSecretMutation,
  useReplayWebhookDestinationEventMutation,
  useRevealWebhookDestinationSecretMutation,
  useWebhookDestinationEventsQuery,
  useWebhookDestinationQuery,
} from "@/src/application/hooks/queries/webhook-destinations";
import { cn } from "@/src/application/lib/utils";
import type { WebhookDeliveryStatus } from "@/src/domain/repositories/workflow";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { PageContent } from "@/src/presentation/components/common/page-content";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Card } from "@/src/presentation/components/ui/card";
import { Input } from "@/src/presentation/components/ui/input";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import { WebhookDeliveriesChart } from "@/src/presentation/workflows/connections/webhook-deliveries-chart";
import { WebhookDestinationFormDialog } from "@/src/presentation/workflows/connections/webhook-destination-form-dialog";

interface DetailProps {
  workflowId: string;
  destinationId: string;
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

export function WebhookDestinationDetail({
  workflowId,
  destinationId,
}: DetailProps) {
  const t = useTranslations("WebhookDestinations");
  const tc = useTranslations("Connections");
  const router = useRouter();
  const { data: destination, isLoading } = useWebhookDestinationQuery(
    workflowId,
    destinationId
  );
  const deleteMutation = useDeleteWebhookDestinationMutation(workflowId);

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const listHref = `/workflows/${workflowId}/connections/destinations/webhooks`;

  if (isLoading) {
    return (
      <PageContent>
        <PageContent.Header
          icon={Webhook}
          title={<Skeleton className="h-6 w-48" />}
          subtitle={tc("subtitle")}
          showBack
          onBack={() => router.push(listHref)}
        />
        <PageContent.Body>
          <DetailSkeleton />
        </PageContent.Body>
      </PageContent>
    );
  }
  if (!destination) {
    return (
      <PageContent>
        <PageContent.Header
          icon={Webhook}
          title={t("title")}
          subtitle={tc("subtitle")}
          showBack
          onBack={() => router.push(listHref)}
        />
        <PageContent.Body>
          <div className="flex flex-1 items-center justify-center">
            <EmptyState
              icon={Webhook}
              title={t("notFoundTitle")}
              description={t("notFound")}
            />
          </div>
        </PageContent.Body>
      </PageContent>
    );
  }

  const handleDelete = () => {
    deleteMutation.mutate(destinationId, {
      onSuccess: () => router.push(listHref),
    });
  };

  return (
    <PageContent>
      <PageContent.Header
        icon={Webhook}
        title={
          <div className="flex min-w-0 items-center gap-3">
            <h1 className="truncate text-xl font-semibold leading-tight tracking-tight">
              {destination.name}
            </h1>
            <Badge
              variant={
                destination.status === "ACTIVE" ? "success" : "secondary"
              }
            >
              {t(`status.${destination.status}`)}
            </Badge>
          </div>
        }
        subtitle={tc("subtitle")}
        showBack
        onBack={() => router.push(listHref)}
        actions={
          <>
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="h-4 w-4" />
              {t("editDestination")}
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="text-destructive"
              onClick={() => setDeleteOpen(true)}
              title={t("deleteDestination")}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </>
        }
      />
      <PageContent.Body scroll={false}>
        <Tabs defaultValue="overview" className="flex min-h-0 flex-1 flex-col">
          <TabsList variant="line" className="shrink-0 border-b border-border">
            <TabsTrigger variant="line" value="overview">
              {t("tabs.overview")}
            </TabsTrigger>
            <TabsTrigger variant="line" value="deliveries">
              {t("tabs.deliveries")}
            </TabsTrigger>
          </TabsList>

          <TabsContent
            value="overview"
            className="mt-6 flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto"
          >
            <OverviewTab
              workflowId={workflowId}
              destinationId={destinationId}
            />
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <DestinationDetailsCard destination={destination} />
              <SigningSecretCard
                workflowId={workflowId}
                destinationId={destinationId}
                hasSecret={destination.hasSecret}
              />
            </div>
          </TabsContent>

          <TabsContent
            value="deliveries"
            className="mt-6 flex min-h-0 flex-1 flex-col"
          >
            <DestinationDeliveries
              workflowId={workflowId}
              destinationId={destinationId}
            />
          </TabsContent>
        </Tabs>
      </PageContent.Body>

      <WebhookDestinationFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        workflowId={workflowId}
        destination={destination}
      />
      <ConfirmDeleteDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onConfirm={handleDelete}
        title={t("deleteTitle")}
        description={t("deleteDescription", { name: destination.name })}
        confirmLabel={t("deleteDestination")}
        cancelLabel={t("dialog.cancel")}
      />
    </PageContent>
  );
}

function OverviewTab({
  workflowId,
  destinationId,
}: {
  workflowId: string;
  destinationId: string;
}) {
  const { data: events = [], isLoading } = useWebhookDestinationEventsQuery(
    workflowId,
    destinationId
  );
  if (isLoading) return <ChartsSkeleton />;
  return <WebhookDeliveriesChart events={events} />;
}

function DestinationDetailsCard({
  destination,
}: {
  destination: import("@/src/domain/entities/webhook-destination").WebhookDestination;
}) {
  const t = useTranslations("WebhookDestinations");
  return (
    <Card className="flex flex-col gap-4 border border-border p-4 ring-0">
      <h3 className="text-sm font-semibold">{t("details.title")}</h3>
      <dl className="flex flex-col gap-3 text-sm">
        <DetailRow label={t("details.id")}>
          <span className="font-mono text-xs">{destination.uuid}</span>
        </DetailRow>
        <DetailRow label={t("details.endpointUrl")}>
          <span className="break-all font-mono text-xs">{destination.url}</span>
        </DetailRow>
        {destination.description ? (
          <DetailRow label={t("details.description")}>
            {destination.description}
          </DetailRow>
        ) : null}
        {destination.apiVersion ? (
          <DetailRow label={t("details.apiVersion")}>
            <span className="font-mono text-xs">{destination.apiVersion}</span>
          </DetailRow>
        ) : null}
        <DetailRow label={t("details.listeningTo")}>
          <div className="flex flex-wrap justify-end gap-1.5">
            {destination.subscribedEvents.map((eventType) => (
              <Badge
                key={eventType}
                variant="secondary"
                className="font-mono text-[10px]"
              >
                {eventType}
              </Badge>
            ))}
          </div>
        </DetailRow>
        <DetailRow label={t("details.createdAt")}>
          {formatDate(destination.createdAt)}
        </DetailRow>
      </dl>
    </Card>
  );
}

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-right">{children}</dd>
    </div>
  );
}

function SigningSecretCard({
  workflowId,
  destinationId,
  hasSecret,
}: {
  workflowId: string;
  destinationId: string;
  hasSecret: boolean;
}) {
  const t = useTranslations("WebhookDestinations");
  const regenerate = useRegenerateWebhookDestinationSecretMutation(workflowId);
  const reveal = useRevealWebhookDestinationSecretMutation(workflowId);
  const [revealed, setRevealed] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleRegenerate = () => {
    regenerate.mutate(destinationId, {
      onSuccess: (data) => {
        setRevealed(data.secret);
        setVisible(false);
        setCopied(false);
      },
    });
  };

  // View always reveals: reuse the value we already hold, otherwise fetch it on
  // demand (the secret is stored server-side, so it can be re-revealed anytime).
  const handleView = () => {
    if (revealed !== null) {
      setVisible(true);
      return;
    }
    reveal.mutate(destinationId, {
      onSuccess: (data) => {
        setRevealed(data.secret);
        setVisible(true);
      },
    });
  };

  const handleCopy = () => {
    if (!revealed) return;
    navigator.clipboard.writeText(revealed);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const MASK = "whsec_••••••••••••••••";
  const showSecret = revealed !== null && visible;

  return (
    <Card className="flex flex-col gap-3 border border-border p-4 ring-0">
      <h3 className="text-sm font-semibold">{t("secret.title")}</h3>
      <p className="text-sm text-muted-foreground">{t("secret.description")}</p>

      <div className="flex items-center gap-2">
        <Input
          value={showSecret ? (revealed as string) : MASK}
          readOnly
          aria-label={t("secret.title")}
          className={cn(
            "flex-1 font-mono text-sm",
            !showSecret && "text-muted-foreground"
          )}
        />

        {/* Always present: View (eye) reveals the secret, then becomes Copy. */}
        {showSecret ? (
          <Button
            variant="outline"
            size="icon"
            onClick={handleCopy}
            aria-label={copied ? t("secret.copied") : t("secret.copy")}
            title={copied ? t("secret.copied") : t("secret.copy")}
          >
            {copied ? (
              <Check className="h-4 w-4 text-success-deep" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
        ) : (
          <ActionButton
            variant="outline"
            size="icon"
            onClick={handleView}
            loading={reveal.isPending}
            icon={<Eye className="h-4 w-4" />}
            aria-label={t("secret.reveal")}
            title={t("secret.reveal")}
          />
        )}

        <Button
          variant="outline"
          size="sm"
          className="h-9 gap-1.5"
          onClick={handleRegenerate}
          disabled={regenerate.isPending}
        >
          <RefreshCw
            className={cn("h-4 w-4", regenerate.isPending && "animate-spin")}
          />
          {hasSecret || revealed ? t("secret.regenerate") : t("secret.reveal")}
        </Button>
      </div>
    </Card>
  );
}

const STATUS_FILTERS: { value: string | undefined; key: string }[] = [
  { value: undefined, key: "all" },
  { value: "DELIVERED", key: "delivered" },
  { value: "FAILED", key: "failed" },
  { value: "PENDING", key: "pending" },
];

const STATUS_VARIANT: Record<
  WebhookDeliveryStatus,
  "success" | "secondary" | "destructive"
> = {
  DELIVERED: "success",
  FAILED: "destructive",
  PENDING: "secondary",
  DELIVERING: "secondary",
  SKIPPED: "secondary",
};

function DestinationDeliveries({
  workflowId,
  destinationId,
}: {
  workflowId: string;
  destinationId: string;
}) {
  const t = useTranslations("WebhookDestinations");
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const { data: events, isLoading } = useWebhookDestinationEventsQuery(
    workflowId,
    destinationId,
    filter
  );
  const {
    mutate: replay,
    isPending: isReplaying,
    variables: replayingId,
  } = useReplayWebhookDestinationEventMutation(workflowId, destinationId);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex shrink-0 items-center justify-end gap-1">
        {STATUS_FILTERS.map((f) => (
          <Button
            key={f.key}
            variant={filter === f.value ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setFilter(f.value)}
            className="h-7 px-2 text-xs font-normal"
          >
            {t(`deliveries.filters.${f.key}`)}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <DeliveriesSkeleton />
      ) : !events || events.length === 0 ? (
        <div className="flex min-h-0 flex-1 items-center justify-center">
          <EmptyState
            icon={Inbox}
            title={t("deliveries.emptyTitle")}
            description={t("deliveries.empty")}
          />
        </div>
      ) : (
        <Card className="min-h-0 flex-1 overflow-hidden border border-border p-0 ring-0">
          <div className="min-h-0 flex-1 overflow-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-muted/30">
                <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                  <th className="px-4 py-3">{t("deliveries.columns.event")}</th>
                  <th className="px-4 py-3">
                    {t("deliveries.columns.status")}
                  </th>
                  <th className="px-4 py-3">
                    {t("deliveries.columns.attempts")}
                  </th>
                  <th className="px-4 py-3">
                    {t("deliveries.columns.createdAt")}
                  </th>
                  <th className="px-4 py-3 text-right">
                    {t("deliveries.columns.actions")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr
                    key={event.uuid}
                    className="border-b border-border/40 last:border-b-0"
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="font-mono text-xs">
                          {event.eventType}
                        </span>
                        <span className="font-mono text-[11px] text-muted-foreground">
                          {event.eventId}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANT[event.deliveryStatus]}>
                        {t(`deliveries.status.${event.deliveryStatus}`)}
                      </Badge>
                      {event.responseStatus ? (
                        <span className="ml-2 font-mono text-xs text-muted-foreground">
                          {event.responseStatus}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {event.attempts}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDate(event.createdAt)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={
                          event.deliveryStatus === "DELIVERED" ||
                          (isReplaying && replayingId === event.uuid)
                        }
                        onClick={() => replay(event.uuid)}
                        title={event.lastError ?? undefined}
                        className="h-7 px-2 text-xs"
                      >
                        <RefreshCw
                          className={`mr-1 h-3.5 w-3.5 ${
                            isReplaying && replayingId === event.uuid
                              ? "animate-spin"
                              : ""
                          }`}
                        />
                        {t("deliveries.replay")}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-9 w-52" />
      <ChartsSkeleton />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Skeleton className="h-56 w-full rounded-xl" />
        <Skeleton className="h-56 w-full rounded-xl" />
      </div>
    </div>
  );
}

function ChartsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {[0, 1].map((i) => (
        <div
          key={i}
          className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-xs"
        >
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3.5 w-20" />
          </div>
          <Skeleton className="h-[200px] w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
}

function DeliveriesSkeleton() {
  return (
    <Card className="min-h-0 flex-1 overflow-hidden border border-border p-0 ring-0">
      <div className="border-b border-border bg-muted/30 px-4 py-3">
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="divide-y divide-border/40">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center justify-between gap-4 px-4 py-3"
          >
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-3.5 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-5 w-16 rounded-4xl" />
            <Skeleton className="h-3.5 w-8" />
            <Skeleton className="h-3.5 w-24" />
            <Skeleton className="h-7 w-16" />
          </div>
        ))}
      </div>
    </Card>
  );
}
