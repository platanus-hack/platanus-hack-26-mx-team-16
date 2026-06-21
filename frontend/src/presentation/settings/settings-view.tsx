"use client";

import {
  Copy,
  FileText,
  Image as ImageIcon,
  Key,
  Pencil,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useSessionStore } from "@/src/application/contexts/session-store";
import {
  useDeleteTenantMutation,
  useRegenerateWebhookKeyMutation,
  useSettingsQuery,
  useUpdateAvatarMutation,
  useUpdateSettingsMutation,
} from "@/src/application/hooks/queries/settings";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/src/presentation/components/ui/avatar";
import { Button } from "@/src/presentation/components/ui/button";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Input } from "@/src/presentation/components/ui/input";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";

export function SettingsView() {
  const t = useTranslations("Settings");
  const router = useRouter();
  const clearTenant = useSessionStore((s) => s.clearTenant);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [localName, setLocalName] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const { data: settings, isLoading } = useSettingsQuery();
  const updateSettings = useUpdateSettingsMutation();
  const uploadAvatar = useUpdateAvatarMutation();
  const regenerateWebhookKey = useRegenerateWebhookKeyMutation();
  const deleteTenant = useDeleteTenantMutation();

  useEffect(() => {
    if (settings) setLocalName(settings.name);
  }, [settings]);

  const handleNameBlur = () => {
    if (settings && localName !== settings.name) {
      updateSettings.mutate(localName);
    }
  };

  const handleAvatarChange = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];
    if (file) uploadAvatar.mutate(file);
  };

  const handleDelete = async () => {
    if (!confirm(t("deleteConfirm"))) return;

    setIsDeleting(true);
    try {
      await deleteTenant.mutateAsync();
      clearTenant();
      router.push("/unassigned");
    } catch {
      setIsDeleting(false);
    }
  };

  if (isLoading) return <FullPageSpinner />;

  if (!settings) {
    return (
      <div className="flex items-center justify-center min-h-100">
        <div className="text-muted-foreground">{t("notFound")}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-3xl font-bold tracking-tight">{t("title")}</h2>

      <div className="flex flex-col">
        <div className="flex items-center gap-4 py-6 border-b border-border">
          <div className="flex items-center justify-center w-10 h-10 shrink-0">
            <Pencil className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 space-y-1">
            <h3 className="text-sm font-medium">{t("orgName.title")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("orgName.description")}
            </p>
          </div>
          <div className="w-48">
            <Input
              value={localName}
              onChange={(e) => setLocalName(e.target.value)}
              onBlur={handleNameBlur}
              placeholder={t("orgName.placeholder")}
            />
          </div>
        </div>

        <div className="flex items-center gap-4 py-6 border-b border-border">
          <div className="flex items-center justify-center w-10 h-10 shrink-0">
            <Key className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 space-y-1">
            <h3 className="text-sm font-medium">{t("orgId.title")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("orgId.description")}
            </p>
          </div>
          <div className="flex gap-2">
            <Input value={settings.tenantId} readOnly className="w-40" />
            <Button
              variant="outline"
              size="icon"
              onClick={() => navigator.clipboard.writeText(settings.tenantId)}
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-4 py-6 border-b border-border">
          <div className="flex items-center justify-center w-10 h-10 shrink-0">
            <ImageIcon className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 space-y-1">
            <h3 className="text-sm font-medium">{t("orgAvatar.title")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("orgAvatar.description")}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              {settings.avatar && <AvatarImage src={settings.avatar} />}
              <AvatarFallback className="bg-primary text-primary-foreground font-semibold">
                {settings.name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarChange}
            />
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-3.5 w-3.5" />
              {t("orgAvatar.upload")}
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-4 py-6 border-b border-border">
          <div className="flex items-center justify-center w-10 h-10 shrink-0">
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 space-y-1">
            <h3 className="text-sm font-medium">{t("maxPages.title")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("maxPages.description")}{" "}
              <a href="#" className="text-primary hover:underline">
                {t("maxPages.descriptionLink")}
              </a>{" "}
              {t("maxPages.descriptionTail")}
            </p>
          </div>
          <div className="text-sm font-medium text-muted-foreground">
            {t("maxPages.value", { count: settings.maxPages })}
          </div>
        </div>

        <div className="flex items-center gap-4 py-6 border-b border-border">
          <div className="flex items-center justify-center w-10 h-10 shrink-0">
            <Key className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 space-y-1">
            <h3 className="text-sm font-medium">{t("webhookKey.title")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("webhookKey.description")}{" "}
              <a href="#" className="text-primary hover:underline">
                {t("webhookKey.learnMore")}
              </a>
            </p>
          </div>
          <div className="flex gap-2">
            <Input
              value={settings.webhookSignatureKey}
              readOnly
              className="w-48 font-mono text-xs"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() =>
                navigator.clipboard.writeText(settings.webhookSignatureKey)
              }
            >
              <Copy className="h-4 w-4" />
            </Button>
            <ActionButton
              variant="outline"
              size="icon"
              onClick={() => regenerateWebhookKey.mutate()}
              loading={regenerateWebhookKey.isPending}
              icon={<RefreshCw className="h-4 w-4" />}
            />
          </div>
        </div>

        <div className="py-8 flex justify-center">
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex items-center gap-2 text-sm text-destructive hover:text-destructive/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className="h-4 w-4" />
            {t("deleteOrg", { name: settings.name })}
          </button>
        </div>
      </div>
    </div>
  );
}
