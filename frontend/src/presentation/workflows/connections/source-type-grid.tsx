"use client";

import {
  ChevronRight,
  FolderInput,
  type LucideIcon,
  Mail,
  MessageCircle,
  Webhook,
} from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useSourcesQuery } from "@/src/application/hooks/queries/sources";
import { Card } from "@/src/presentation/components/ui/card";
import { ComingSoonTile } from "@/src/presentation/workflows/connections/coming-soon-tile";

/**
 * Grid of source (origin) connection types, mirroring DestinationTypeGrid. The
 * first tile (Webhook) is active and links to the workflow's ingest endpoints;
 * the rest are placeholders until their adapters land (Email, WhatsApp, Drive —
 * see product/specs/connections/spec.md §5 / §10).
 */
export function SourceTypeGrid({
  workflowSlug,
  workflowUuid,
}: {
  workflowSlug: string;
  workflowUuid: string | null;
}) {
  const t = useTranslations("Connections");
  const { data: sources = [] } = useSourcesQuery(workflowUuid);

  const comingSoon: { icon: LucideIcon; title: string; description: string }[] =
    [
      {
        icon: Mail,
        title: t("emailOriginTitle"),
        description: t("emailOriginDescription"),
      },
      {
        icon: MessageCircle,
        title: t("whatsappTitle"),
        description: t("whatsappOriginDescription"),
      },
      {
        icon: FolderInput,
        title: t("driveTitle"),
        description: t("driveOriginDescription"),
      },
    ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <WebhookSourceTile
        workflowSlug={workflowSlug}
        count={sources.length}
        title={t("webhookTitle")}
        description={t("webhookSourceDescription")}
        cta={t("manageWebhooks")}
        configuredLabel={t("configuredCount", { count: sources.length })}
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

function WebhookSourceTile({
  workflowSlug,
  count,
  title,
  description,
  cta,
  configuredLabel,
}: {
  workflowSlug: string;
  count: number;
  title: string;
  description: string;
  cta: string;
  configuredLabel: string;
}) {
  return (
    <Link
      href={`/workflows/${workflowSlug}/connections/sources/webhooks`}
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
