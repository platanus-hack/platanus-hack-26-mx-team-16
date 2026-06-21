"use client";

import { Mail, Slack } from "lucide-react";
import { useEffect, useState } from "react";

import { authHttp } from "@/src/infrastructure/http/client";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import { Switch } from "@/src/presentation/components/ui/switch";

/**
 * Account-level alert-channel preferences, wired to the real backend
 * (`GET`/`PUT /v1/me/alerts`, sites module). The data model is intentionally
 * minimal (06-data-model §3.6): an email on/off flag plus an optional Slack
 * webhook URL — Slack is "enabled" when a webhook is set. We follow the new
 * data-access convention: call `authHttp` directly, no repository wrapper.
 */
type AlertPrefs = {
  emailEnabled: boolean;
  slackWebhookUrl: string | null;
};

export function NotificationsView() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [emailEnabled, setEmailEnabled] = useState(true);
  const [slackEnabled, setSlackEnabled] = useState(false);
  const [slackUrl, setSlackUrl] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await authHttp.get<{ data: AlertPrefs }>("/v1/me/alerts");
        if (!active) return;
        const prefs = res.data.data;
        setEmailEnabled(prefs.emailEnabled);
        setSlackEnabled(Boolean(prefs.slackWebhookUrl));
        setSlackUrl(prefs.slackWebhookUrl ?? "");
      } catch {
        if (active) setLoadError(true);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(false);
    setSaveSuccess(false);
    const slackWebhookUrl =
      slackEnabled && slackUrl.trim() ? slackUrl.trim() : null;
    try {
      await authHttp.put("/v1/me/alerts", { emailEnabled, slackWebhookUrl });
      setSlackEnabled(Boolean(slackWebhookUrl));
      setSaveSuccess(true);
    } catch {
      setSaveError(true);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <div className="text-muted-foreground">Cargando…</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Notificaciones
        </h1>
        <p className="text-[15px] text-muted-foreground">
          Decide por dónde Owliver te avisa de cambios en tus sitios.
        </p>
      </header>

      {loadError && (
        <p className="rounded-xl border border-destructive/40 bg-card px-4 py-3 text-sm text-destructive">
          No se pudieron cargar tus preferencias. Intenta de nuevo.
        </p>
      )}

      {/* Channels */}
      <section className="flex flex-col rounded-2xl border border-outline-variant bg-card p-6">
        <h2 className="text-base font-semibold text-foreground">Canales</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Por dónde te llegan las alertas.
        </p>

        <div className="flex items-center gap-3 py-1.5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-container">
            <Mail className="size-4 text-primary" />
          </span>
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="text-sm font-medium text-foreground">
              Correo electrónico
            </span>
            <span className="text-sm text-muted-foreground">
              Resumen y alertas críticas en tu bandeja.
            </span>
          </div>
          <Switch checked={emailEnabled} onCheckedChange={setEmailEnabled} />
        </div>

        <div className="my-2 h-px w-full bg-outline-variant" />

        <div className="flex flex-col gap-3 py-1.5">
          <div className="flex items-center gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-container">
              <Slack className="size-4 text-primary" />
            </span>
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="text-sm font-medium text-foreground">Slack</span>
              <span className="text-sm text-muted-foreground">
                Notifica a tu canal de seguridad con un webhook entrante.
              </span>
            </div>
            <Switch checked={slackEnabled} onCheckedChange={setSlackEnabled} />
          </div>

          {slackEnabled && (
            <div className="flex flex-col gap-1.5 pl-12">
              <Label htmlFor="slackUrl">Webhook de Slack</Label>
              <Input
                id="slackUrl"
                type="url"
                inputMode="url"
                value={slackUrl}
                onValueChange={setSlackUrl}
                placeholder="https://hooks.slack.com/services/…"
                className="font-mono text-sm"
              />
              <span className="text-xs text-outline">
                Pega tu webhook entrante para activar las alertas en Slack.
              </span>
            </div>
          )}
        </div>
      </section>

      <div className="flex items-center gap-3">
        <ActionButton type="button" onClick={handleSave} loading={saving}>
          {saving ? "Guardando…" : "Guardar preferencias"}
        </ActionButton>
        {saveSuccess && (
          <span className="text-sm text-success-deep">
            Preferencias guardadas.
          </span>
        )}
        {saveError && (
          <span className="text-sm text-destructive">
            No se pudieron guardar. Intenta de nuevo.
          </span>
        )}
      </div>
    </div>
  );
}
