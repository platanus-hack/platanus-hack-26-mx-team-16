"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import {
  ConnectionProvider,
  type CreateConnectionPayload,
} from "@/src/domain/entities/connection";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogDescription,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { PROVIDER_ICON } from "./connection-providers";
import { CONNECTIONS_QUERY_KEY, connectionRepo } from "./connection-repo";

type HttpAuth = "bearer" | "api_key";

interface FormState {
  displayName: string;
  // HTTP
  baseUrl: string;
  httpAuth: HttpAuth;
  apiKeyHeader: string;
  token: string;
  // Slack
  channelId: string;
  botToken: string;
  // WhatsApp
  phoneNumberId: string;
  verifyToken: string;
  appSecret: string;
  accessToken: string;
}

const EMPTY_FORM: FormState = {
  displayName: "",
  baseUrl: "",
  httpAuth: "bearer",
  apiKeyHeader: "",
  token: "",
  channelId: "",
  botToken: "",
  phoneNumberId: "",
  verifyToken: "",
  appSecret: "",
  accessToken: "",
};

function buildPayload(
  provider: ConnectionProvider,
  form: FormState
): CreateConnectionPayload {
  switch (provider) {
    case ConnectionProvider.HTTP:
      return {
        provider,
        displayName: form.displayName,
        config: {
          base_url: form.baseUrl,
          auth: form.httpAuth,
          ...(form.httpAuth === "api_key"
            ? { api_key_header: form.apiKeyHeader.trim() || "X-Api-Key" }
            : {}),
        },
        secret: form.token || null,
      };
    case ConnectionProvider.SLACK:
      return {
        provider,
        displayName: form.displayName,
        config: { channel_id: form.channelId.trim() },
        secret: form.botToken || null,
      };
    case ConnectionProvider.WHATSAPP:
      return {
        provider,
        displayName: form.displayName,
        config: {
          phone_number_id: form.phoneNumberId.trim(),
          verify_token: form.verifyToken.trim(),
          app_secret: form.appSecret.trim(),
        },
        secret: form.accessToken || null,
      };
    default:
      return { provider, displayName: form.displayName };
  }
}

function isComplete(provider: ConnectionProvider, form: FormState): boolean {
  if (!form.displayName.trim()) return false;
  switch (provider) {
    case ConnectionProvider.HTTP:
      return Boolean(form.baseUrl.trim() && form.token.trim());
    case ConnectionProvider.SLACK:
      return Boolean(form.channelId.trim() && form.botToken.trim());
    case ConnectionProvider.WHATSAPP:
      return Boolean(
        form.phoneNumberId.trim() &&
          form.verifyToken.trim() &&
          form.appSecret.trim() &&
          form.accessToken.trim()
      );
    default:
      return true;
  }
}

/**
 * Step two of the "add integration" flow: the creation modal for a single
 * provider. The fields rendered differ per provider (HTTP API, Slack, WhatsApp
 * Cloud) and the config keys mirror exactly what each backend adapter reads.
 */
export function ConnectionFormDialog({
  provider,
  open,
  onOpenChange,
}: {
  provider: ConnectionProvider | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("ConnectionsOrg");
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);

  // Reset the form each time a provider modal opens (open toggles per open).
  useEffect(() => {
    if (open) {
      setForm(EMPTY_FORM);
      setError(null);
    }
  }, [open]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!provider) return;
      const res = await connectionRepo.create(buildPayload(provider, form));
      if (isErrorFeedback(res)) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CONNECTIONS_QUERY_KEY });
      onOpenChange(false);
    },
    onError: (e: Error) => setError(e.message),
  });

  if (!provider) return null;

  const Icon = PROVIDER_ICON[provider];
  const providerLabel = t(`provider.${provider}`);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="w-full max-w-md p-6">
        <div className="mb-1 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <DialogTitle className="text-lg font-semibold">
            {t("form.title", { provider: providerLabel })}
          </DialogTitle>
        </div>
        <DialogDescription className="mb-5 text-sm text-muted-foreground">
          {t("form.description")}
        </DialogDescription>

        <div className="space-y-4">
          <Field label={t("form.displayName")}>
            <Input
              value={form.displayName}
              onChange={(e) => set("displayName", e.target.value)}
              placeholder={t("form.displayNamePlaceholder")}
            />
          </Field>

          {provider === ConnectionProvider.HTTP && (
            <>
              <Field label={t("form.http.baseUrl")}>
                <Input
                  value={form.baseUrl}
                  onChange={(e) => set("baseUrl", e.target.value)}
                  placeholder={t("form.http.baseUrlPlaceholder")}
                />
              </Field>
              <Field label={t("form.http.auth")}>
                <Select
                  value={form.httpAuth}
                  onValueChange={(v) => v && set("httpAuth", v as HttpAuth)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bearer">
                      {t("form.http.authBearer")}
                    </SelectItem>
                    <SelectItem value="api_key">
                      {t("form.http.authApiKey")}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              {form.httpAuth === "api_key" && (
                <Field label={t("form.http.apiKeyHeader")}>
                  <Input
                    value={form.apiKeyHeader}
                    onChange={(e) => set("apiKeyHeader", e.target.value)}
                    placeholder="X-Api-Key"
                  />
                </Field>
              )}
              <Field label={t("form.http.token")}>
                <Input
                  type="password"
                  value={form.token}
                  onChange={(e) => set("token", e.target.value)}
                  placeholder={t("form.http.tokenPlaceholder")}
                />
              </Field>
            </>
          )}

          {provider === ConnectionProvider.SLACK && (
            <>
              <Field label={t("form.slack.channelId")}>
                <Input
                  value={form.channelId}
                  onChange={(e) => set("channelId", e.target.value)}
                  placeholder={t("form.slack.channelIdPlaceholder")}
                />
              </Field>
              <Field label={t("form.slack.botToken")}>
                <Input
                  type="password"
                  value={form.botToken}
                  onChange={(e) => set("botToken", e.target.value)}
                  placeholder={t("form.slack.botTokenPlaceholder")}
                />
              </Field>
            </>
          )}

          {provider === ConnectionProvider.WHATSAPP && (
            <>
              <Field label={t("form.whatsapp.phoneNumberId")}>
                <Input
                  value={form.phoneNumberId}
                  onChange={(e) => set("phoneNumberId", e.target.value)}
                  placeholder="123456789012345"
                />
              </Field>
              <Field label={t("form.whatsapp.verifyToken")}>
                <Input
                  value={form.verifyToken}
                  onChange={(e) => set("verifyToken", e.target.value)}
                />
              </Field>
              <Field label={t("form.whatsapp.appSecret")}>
                <Input
                  type="password"
                  value={form.appSecret}
                  onChange={(e) => set("appSecret", e.target.value)}
                />
              </Field>
              <Field label={t("form.whatsapp.accessToken")}>
                <Input
                  type="password"
                  value={form.accessToken}
                  onChange={(e) => set("accessToken", e.target.value)}
                />
              </Field>
            </>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <DialogClose
              render={<Button variant="outline">{t("form.cancel")}</Button>}
            />
            <ActionButton
              disabled={!isComplete(provider, form)}
              loading={createMutation.isPending}
              onClick={() => {
                setError(null);
                createMutation.mutate();
              }}
            >
              {t("form.submit")}
            </ActionButton>
          </div>
        </div>
      </DialogPopup>
    </Dialog>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
    </div>
  );
}
