"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import {
  useCreateWebhookDestinationMutation,
  useUpdateWebhookDestinationMutation,
} from "@/src/application/hooks/queries/webhook-destinations";
import {
  type WebhookDestination,
  WEBHOOK_EVENT_TYPES,
} from "@/src/domain/entities/webhook-destination";
import { Button } from "@/src/presentation/components/ui/button";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Checkbox } from "@/src/presentation/components/ui/checkbox";
import {
  Dialog,
  DialogBackdrop,
  DialogDescription,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";
import { Switch } from "@/src/presentation/components/ui/switch";

interface WebhookDestinationFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowId: string;
  /** When provided the dialog edits this destination; otherwise it creates one. */
  destination?: WebhookDestination;
}

export function WebhookDestinationFormDialog({
  open,
  onOpenChange,
  workflowId,
  destination,
}: WebhookDestinationFormDialogProps) {
  const t = useTranslations("WebhookDestinations");
  const isEdit = !!destination;

  const createMutation = useCreateWebhookDestinationMutation(workflowId);
  const updateMutation = useUpdateWebhookDestinationMutation(workflowId);

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [events, setEvents] = useState<string[]>([...WEBHOOK_EVENT_TYPES]);
  const [error, setError] = useState<string | null>(null);

  // Reset the form whenever the dialog opens (so create starts blank and edit
  // is pre-filled with the latest destination values).
  useEffect(() => {
    if (!open) return;
    setName(destination?.name ?? "");
    setUrl(destination?.url ?? "");
    setDescription(destination?.description ?? "");
    setEnabled(destination?.enabled ?? true);
    setEvents(destination?.subscribedEvents ?? [...WEBHOOK_EVENT_TYPES]);
    setError(null);
  }, [open, destination]);

  const toggleEvent = (eventType: string) =>
    setEvents((prev) =>
      prev.includes(eventType)
        ? prev.filter((e) => e !== eventType)
        : [...prev, eventType]
    );

  const isPending = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = () => {
    setError(null);
    const payload = {
      name: name.trim(),
      url: url.trim(),
      description: description.trim() || null,
      enabled,
      subscribedEvents: events,
    };
    const onError = (e: Error) => setError(e.message);
    const onSuccess = () => onOpenChange(false);

    if (isEdit) {
      updateMutation.mutate(
        { destinationId: destination.uuid, payload },
        { onError, onSuccess }
      );
    } else {
      createMutation.mutate(payload, { onError, onSuccess });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="w-full max-w-lg p-6">
        <DialogTitle className="mb-1 text-lg font-semibold">
          {isEdit ? t("dialog.editTitle") : t("dialog.createTitle")}
        </DialogTitle>
        <DialogDescription className="mb-5 text-sm text-muted-foreground">
          {t("dialog.description")}
        </DialogDescription>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">{t("dialog.name")}</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("dialog.namePlaceholder")}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">{t("dialog.url")}</label>
            <Input
              type="url"
              inputMode="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://api.your-org.com/webhooks/doxiq"
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">{t("dialog.urlHint")}</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">
              {t("dialog.descriptionLabel")}
            </label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("dialog.descriptionPlaceholder")}
            />
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">{t("dialog.events")}</span>
            <div className="flex flex-col gap-2">
              {WEBHOOK_EVENT_TYPES.map((eventType) => (
                <label
                  key={eventType}
                  className="flex cursor-pointer items-center gap-2.5 rounded-md border border-border/60 px-3 py-2"
                >
                  <Checkbox
                    checked={events.includes(eventType)}
                    onCheckedChange={() => toggleEvent(eventType)}
                  />
                  <span className="font-mono text-xs">{eventType}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col">
              <span className="text-sm font-medium">{t("dialog.enabled")}</span>
              <span className="text-xs text-muted-foreground">
                {t("dialog.enabledHint")}
              </span>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {t("dialog.cancel")}
            </Button>
            <ActionButton
              disabled={!name.trim() || !url.trim()}
              loading={isPending}
              onClick={handleSubmit}
            >
              {isEdit ? t("dialog.save") : t("dialog.create")}
            </ActionButton>
          </div>
        </div>
      </DialogPopup>
    </Dialog>
  );
}
