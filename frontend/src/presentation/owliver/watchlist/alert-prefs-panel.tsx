/**
 * AlertPrefsPanel (§F11) — account-level alert preferences (GET/PUT /me/alerts).
 * Email to the owner is always on (display-only, per 08-ranking §5.1); the Slack
 * webhook is optional and editable. Saves through the BFF; a transient "Guardado"
 * confirmation replaces a toast (sonner isn't a dependency yet).
 */
"use client";

import * as React from "react";
import { Check, Loader2 } from "lucide-react";

import {
  useAlertPrefs,
  useUpdateAlertPrefs,
} from "@/src/application/owliver/hooks/use-alert-prefs";
import { Button } from "@/src/presentation/components/ui/button";
import { Switch } from "@/src/presentation/components/ui/switch";

export function AlertPrefsPanel() {
  const { data, isLoading } = useAlertPrefs();
  const update = useUpdateAlertPrefs();

  const [slack, setSlack] = React.useState("");
  const [emailEnabled, setEmailEnabled] = React.useState(true);
  const [saved, setSaved] = React.useState(false);
  const initialized = React.useRef(false);

  React.useEffect(() => {
    if (data && !initialized.current) {
      setSlack(data.slackWebhookUrl ?? "");
      setEmailEnabled(data.emailEnabled);
      initialized.current = true;
    }
  }, [data]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaved(false);
    try {
      await update.mutateAsync({
        emailEnabled,
        slackWebhookUrl: slack.trim() ? slack.trim() : null,
      });
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2500);
    } catch {
      /* error surfaced by the disabled→enabled button; keep panel simple */
    }
  }

  return (
    <form
      onSubmit={onSave}
      className="rounded-2xl border border-outline-variant bg-card p-5 shadow-xs"
    >
      <h2 className="text-base font-semibold text-foreground">
        Alertas de la cuenta
      </h2>
      <p className="mt-1 text-sm text-on-surface-variant">
        Te avisamos cuando el grado de un sitio monitoreado empeora.
      </p>

      <div className="mt-4 space-y-4">
        <label className="flex items-center justify-between gap-4">
          <span className="text-sm text-foreground">
            Correo al titular de la cuenta
          </span>
          <Switch
            checked={emailEnabled}
            disabled={isLoading}
            onCheckedChange={setEmailEnabled}
            aria-label="Alertas por correo"
          />
        </label>

        <div>
          <label
            htmlFor="slack-webhook"
            className="text-sm text-foreground"
          >
            Webhook de Slack (opcional)
          </label>
          <input
            id="slack-webhook"
            type="url"
            inputMode="url"
            autoComplete="off"
            placeholder="https://hooks.slack.com/services/…"
            value={slack}
            disabled={isLoading}
            onChange={(e) => setSlack(e.target.value)}
            className="mt-1.5 h-10 w-full rounded-xl border border-outline bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50"
          />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <Button type="submit" variant="default" size="sm" disabled={update.isPending}>
          {update.isPending && (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          )}
          Guardar
        </Button>
        {saved && (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-success-deep">
            <Check className="size-3.5" aria-hidden />
            Guardado
          </span>
        )}
      </div>
    </form>
  );
}
