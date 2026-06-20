"use client";

import {
  ChevronRight,
  Mail,
  MessageCircle,
  MessageSquare,
  Webhook,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useWebhookDestinationsQuery } from "@/src/application/hooks/queries/webhook-destinations";
import { Card } from "@/src/presentation/components/ui/card";
import { ComingSoonTile } from "@/src/presentation/workflows/connections/coming-soon-tile";

/**
 * Grid of destination connection types (3 columns on large screens). The first
 * tile (Webhooks) is always present and active, linking to the configured
 * webhook destinations. The rest are placeholders until their adapters land.
 */
export function DestinationTypeGrid({ workflowId }: { workflowId: string }) {
  const t = useTranslations("Connections");
  const { data: destinations = [] } = useWebhookDestinationsQuery(workflowId);

  const comingSoon: { icon: LucideIcon; title: string; description: string }[] =
    [
      {
        icon: MessageSquare,
        title: t("slackTitle"),
        description: t("slackDescription"),
      },
      {
        icon: Mail,
        title: t("emailDestinationTitle"),
        description: t("emailDestinationDescription"),
      },
      {
        icon: MessageCircle,
        title: t("whatsappTitle"),
        description: t("whatsappDescription"),
      },
    ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <WebhookTile
        workflowId={workflowId}
        count={destinations.length}
        title={t("webhookTitle")}
        description={t("webhookDescription")}
        cta={t("manageWebhooks")}
        configuredLabel={t("configuredCount", { count: destinations.length })}
      />
      {comingSoon.map((tile) => (
        <ComingSoonTile
          key={tile.title}
          icon={tile.icon}
          title={tile.title}
          description={tile.description}
          comingSoonLabel={t("comingSoon")}
        />
      ))}
    </div>
  );
}

function WebhookTile({
  workflowId,
  count,
  title,
  description,
  cta,
  configuredLabel,
}: {
  workflowId: string;
  count: number;
  title: string;
  description: string;
  cta: string;
  configuredLabel: string;
}) {
  return (
    <Link
      href={`/workflows/${workflowId}/connections/destinations/webhooks`}
      className="group h-full"
    >
      <Card className="flex h-full flex-col gap-3 border border-border p-5 ring-0 transition-shadow hover:shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Webhook className="h-5 w-5" />
          </div>
          {count > 0 ? (
            <span className="text-xs text-muted-foreground">
              {configuredLabel}
            </span>
          ) : null}
        </div>
        <h2 className="text-sm font-semibold">{title}</h2>
        <p className="flex-1 text-sm text-muted-foreground">{description}</p>
        <span className="flex items-center gap-1 text-sm font-medium text-primary">
          {cta}
          <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </span>
      </Card>
    </Link>
  );
}
