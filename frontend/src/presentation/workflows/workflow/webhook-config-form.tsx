"use client";

import { Copy, RefreshCw, Webhook } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import {
  useRegenerateWebhookSecretMutation,
  useUpdateWorkflowMutation,
  useWorkflowQuery,
} from "@/src/application/hooks/queries/workflows";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";
import { Switch } from "@/src/presentation/components/ui/switch";
import { WebhookDeliveryLog } from "@/src/presentation/workflows/workflow/webhook-delivery-log";

const WEBHOOK_EVENT_TYPES = ["document.extracted", "document.failed"] as const;

interface WebhookConfigFormProps {
  // The route param `wfSlug` carries the workflow uuid used by the API.
  workflowSlug: string;
}

export function WebhookConfigForm({ workflowSlug }: WebhookConfigFormProps) {
  const t = useTranslations("DataExportConfig");
  const { data: workflow } = useWorkflowQuery(workflowSlug);
  const updateWorkflow = useUpdateWorkflowMutation();
  const regenerateSecret = useRegenerateWebhookSecretMutation();

  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookEnabled, setWebhookEnabled] = useState(false);
  const [webhookEvents, setWebhookEvents] = useState<string[]>([]);
  const [revealedSecret, setRevealedSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!workflow) return;
    setWebhookUrl(workflow.webhookUrl ?? "");
    setWebhookEnabled(workflow.webhookEnabled ?? false);
    setWebhookEvents(workflow.webhookEvents ?? []);
  }, [workflow]);

  const handleToggleEvent = (eventType: string) => {
    setWebhookEvents((prev) =>
      prev.includes(eventType)
        ? prev.filter((evt) => evt !== eventType)
        : [...prev, eventType]
    );
  };

  const handleSaveWebhooks = () => {
    updateWorkflow.mutate({
      uuid: workflowSlug,
      payload: {
        webhookUrl: webhookUrl.trim() || null,
        webhookEnabled,
        webhookEvents,
      },
    });
  };

  const handleRegenerateSecret = () => {
    regenerateSecret.mutate(workflowSlug, {
      onSuccess: (data) => setRevealedSecret(data.webhookSecret),
    });
  };

  const handleCopySecret = () => {
    if (!revealedSecret) return;
    navigator.clipboard.writeText(revealedSecret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <Webhook className="h-5 w-5 text-muted-foreground" />
        <h3 className="text-base font-semibold">{t("webhooksTitle")}</h3>
      </div>

      {/* Endpoint URL */}
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">{t("webhookUrlTitle")}</span>
        <p className="text-sm text-muted-foreground">
          {t("webhookUrlDescription")}
        </p>
        <Input
          type="url"
          inputMode="url"
          placeholder={t("webhookUrlPlaceholder")}
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          className="font-mono text-sm"
        />
      </div>

      {/* Enabled toggle */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col">
          <span className="text-sm font-medium">{t("webhookEnabled")}</span>
          <span className="text-sm text-muted-foreground">
            {t("webhookEnabledDescription")}
          </span>
        </div>
        <Switch checked={webhookEnabled} onCheckedChange={setWebhookEnabled} />
      </div>

      {/* Event subscription */}
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">{t("webhookEventsTitle")}</span>
        <div className="flex flex-col gap-2">
          {WEBHOOK_EVENT_TYPES.map((eventType) => (
            <div
              key={eventType}
              className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2"
            >
              <span className="font-mono text-xs">{eventType}</span>
              <Switch
                checked={webhookEvents.includes(eventType)}
                onCheckedChange={() => handleToggleEvent(eventType)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <ActionButton
          size="sm"
          onClick={handleSaveWebhooks}
          loading={updateWorkflow.isPending}
        >
          {t("save")}
        </ActionButton>
        {updateWorkflow.isError ? (
          <span className="text-sm text-destructive">{t("saveError")}</span>
        ) : null}
        {updateWorkflow.isSuccess ? (
          <span className="text-sm text-muted-foreground">{t("saved")}</span>
        ) : null}
      </div>

      {/* Signing secret */}
      <div className="flex flex-col gap-2 border-t border-border/50 pt-4">
        <span className="text-sm font-medium">{t("webhookSecretTitle")}</span>
        <p className="text-sm text-muted-foreground">
          {t("webhookSecretDescription")}{" "}
          <a
            href="https://docs.llamit.ai/webhooks"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:text-blue-600 underline"
          >
            {t("learnMore")}
          </a>
        </p>
        {revealedSecret ? (
          <>
            <div className="flex items-center gap-2">
              <Input
                type="text"
                value={revealedSecret}
                readOnly
                className="flex-1 font-mono text-sm"
              />
              <Button
                variant="outline"
                size="icon"
                onClick={handleCopySecret}
                title={copied ? t("copied") : t("copyTitle")}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-amber-600">
              {t("webhookSecretRevealOnce")}
            </p>
          </>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={handleRegenerateSecret}
            disabled={regenerateSecret.isPending}
            className="self-start"
          >
            <RefreshCw
              className={`mr-1 h-4 w-4 ${
                regenerateSecret.isPending ? "animate-spin" : ""
              }`}
            />
            {t("regenerateTitle")}
          </Button>
        )}
      </div>

      {/* Delivery log + replay (§10) */}
      <div className="border-t border-border/50 pt-4">
        <WebhookDeliveryLog workflowUuid={workflowSlug} />
      </div>
    </div>
  );
}
