"use client";

import { ChevronRight, Webhook } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type MutableRefObject, useEffect, useState } from "react";
import { useWebhookDestinationsQuery } from "@/src/application/hooks/queries/webhook-destinations";
import { cn } from "@/src/application/lib/utils";
import type { WebhookDestination } from "@/src/domain/entities/webhook-destination";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Card } from "@/src/presentation/components/ui/card";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import { WebhookDestinationFormDialog } from "@/src/presentation/workflows/connections/webhook-destination-form-dialog";

export function WebhookDestinationsList({
  workflowId,
  onAddRef,
}: {
  workflowId: string;
  onAddRef?: MutableRefObject<(() => void) | null>;
}) {
  const t = useTranslations("WebhookDestinations");
  const { data: destinations = [], isLoading } =
    useWebhookDestinationsQuery(workflowId);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Expose "open create dialog" to the page so the PageHeader action can
  // trigger it (mirrors knowledge-content / analysis-rules-content).
  useEffect(() => {
    if (!onAddRef) return;
    onAddRef.current = () => setDialogOpen(true);
    return () => {
      onAddRef.current = null;
    };
  }, [onAddRef]);

  return (
    <div className="flex flex-1 flex-col gap-4">
      {isLoading ? (
        <DestinationsSkeleton />
      ) : destinations.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <EmptyState
            icon={Webhook}
            title={t("emptyTitle")}
            description={t("emptyDescription")}
            actionLabel={t("addDestination")}
            onAction={() => setDialogOpen(true)}
          />
        </div>
      ) : (
        <Card className="overflow-hidden border border-border p-0 ring-0">
          <div className="divide-y divide-border">
            {destinations.map((destination) => (
              <DestinationRow
                key={destination.uuid}
                workflowId={workflowId}
                destination={destination}
              />
            ))}
          </div>
        </Card>
      )}

      <WebhookDestinationFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        workflowId={workflowId}
      />
    </div>
  );
}

function DestinationRow({
  workflowId,
  destination,
}: {
  workflowId: string;
  destination: WebhookDestination;
}) {
  const t = useTranslations("WebhookDestinations");
  const isActive = destination.status === "ACTIVE";

  return (
    <Link
      href={`/workflows/${workflowId}/connections/destinations/webhooks/${destination.uuid}`}
      className={cn(
        "group flex items-center gap-4 px-4 py-3 outline-none transition-colors",
        "hover:bg-muted/40",
        "focus-visible:relative focus-visible:z-10 focus-visible:bg-muted/40 focus-visible:ring-[3px] focus-visible:ring-inset focus-visible:ring-ring/50"
      )}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        <Webhook className="h-5 w-5" />
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate text-sm font-medium" title={destination.name}>
          {destination.name}
        </span>
        <span
          className="truncate font-mono text-xs text-muted-foreground"
          title={destination.url}
        >
          {destination.url}
        </span>
      </div>

      <Badge variant={isActive ? "success" : "secondary"}>
        <span className="size-1.5 shrink-0 rounded-full bg-current" />
        {t(`status.${destination.status}`)}
      </Badge>

      <span className="hidden w-28 shrink-0 text-right text-xs text-muted-foreground sm:block">
        {t("eventsCount", { count: destination.subscribedEvents.length })}
      </span>

      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 motion-reduce:transform-none motion-reduce:transition-none" />
    </Link>
  );
}

function DestinationsSkeleton() {
  return (
    <Card className="overflow-hidden border border-border p-0 ring-0">
      <div className="divide-y divide-border">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3">
            <Skeleton className="h-10 w-10 shrink-0 rounded-lg" />
            <div className="flex min-w-0 flex-1 flex-col gap-1.5">
              <Skeleton className="h-3.5 w-40" />
              <Skeleton className="h-3 w-56 max-w-full" />
            </div>
            <Skeleton className="h-5 w-16 rounded-4xl" />
            <Skeleton className="hidden h-3 w-20 sm:block" />
            <Skeleton className="h-4 w-4 shrink-0" />
          </div>
        ))}
      </div>
    </Card>
  );
}
