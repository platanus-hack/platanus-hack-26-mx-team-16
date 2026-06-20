"use client";

import { RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  useReplayWebhookEventMutation,
  useWorkflowEventsQuery,
} from "@/src/application/hooks/queries/workflows";
import type {
  WebhookDeliveryStatus,
  WebhookEvent,
} from "@/src/domain/repositories/workflow";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";

const STATUS_FILTERS: { value: string | undefined; key: string }[] = [
  { value: undefined, key: "all" },
  { value: "DELIVERED", key: "delivered" },
  { value: "FAILED", key: "failed" },
  { value: "PENDING", key: "pending" },
  { value: "SKIPPED", key: "skipped" },
];

const STATUS_VARIANT: Record<
  WebhookDeliveryStatus,
  "default" | "secondary" | "destructive"
> = {
  DELIVERED: "default",
  FAILED: "destructive",
  PENDING: "secondary",
  DELIVERING: "secondary",
  SKIPPED: "secondary",
};

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

export function WebhookDeliveryLog({ workflowUuid }: { workflowUuid: string }) {
  const t = useTranslations("DataExportConfig");
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const { data: events, isLoading } = useWorkflowEventsQuery(
    workflowUuid,
    filter
  );
  const {
    mutate: replay,
    isPending: isReplaying,
    variables: replayingId,
  } = useReplayWebhookEventMutation(workflowUuid);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-base font-semibold">{t("deliveryLogTitle")}</h4>
        <div className="flex items-center gap-1">
          {STATUS_FILTERS.map((f) => (
            <Button
              key={f.key}
              variant={filter === f.value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setFilter(f.value)}
              className="h-7 px-2 text-xs font-normal"
            >
              {t(`deliveryLogFilters.${f.key}`)}
            </Button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          {t("loading")}
        </p>
      ) : !events || events.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          {t("deliveryLogEmpty")}
        </p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full">
            <thead className="bg-muted/20">
              <tr className="border-b border-border/50 text-left text-sm font-normal text-muted-foreground">
                <th className="px-4 py-3">{t("deliveryLogColumns.event")}</th>
                <th className="px-4 py-3">{t("deliveryLogColumns.status")}</th>
                <th className="px-4 py-3">{t("deliveryLogColumns.attempts")}</th>
                <th className="px-4 py-3">{t("deliveryLogColumns.createdAt")}</th>
                <th className="px-4 py-3 text-right">
                  {t("deliveryLogColumns.actions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {events.map((event: WebhookEvent) => (
                <tr
                  key={event.uuid}
                  className="border-b border-border/30 text-sm last:border-b-0"
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
                      {t(`deliveryLogStatus.${event.deliveryStatus}`)}
                    </Badge>
                    {event.responseStatus ? (
                      <span className="ml-2 text-xs text-muted-foreground">
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
                      {t("deliveryLogActionReplay")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
