"use client";

import { Check, Copy, Mail, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { usePermissions } from "@/src/application/hooks/use-permissions";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type { PendingInvitation } from "@/src/domain/repositories/tenant-user";
import {
  Avatar,
  AvatarFallback,
} from "@/src/presentation/components/ui/avatar";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";

interface Props {
  invitation: PendingInvitation;
  roles: TenantRole[];
  onCancel: (invitationId: string) => void;
}

function buildInvitationUrl(token: string): string {
  if (typeof window === "undefined") return `/invitations/${token}`;
  return `${window.location.origin}/invitations/${encodeURIComponent(token)}`;
}

export function PendingInvitationItem({ invitation, roles, onCancel }: Props) {
  const t = useTranslations("PendingInvitation");
  const role = roles.find((r) => r.uuid === invitation.tenantRoleId);
  const { hasPermission } = usePermissions();
  const canCancel = hasPermission("tenant_users.delete");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1800);
    return () => clearTimeout(timer);
  }, [copied]);

  const formatExpiry = (expiresAt: string | null): string => {
    if (!expiresAt) return t("noExpiry");
    const ms = new Date(expiresAt).getTime() - Date.now();
    if (Number.isNaN(ms)) return t("noExpiry");
    if (ms <= 0) return t("expired");
    const days = Math.floor(ms / 86_400_000);
    if (days >= 1) return t("expiresInDays", { days });
    const hours = Math.max(1, Math.floor(ms / 3_600_000));
    return t("expiresInHours", { hours });
  };

  const handleCopy = async () => {
    const url = buildInvitationUrl(invitation.token);
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
        setCopied(true);
      } finally {
        document.body.removeChild(ta);
      }
    }
  };

  return (
    <div className="flex items-center gap-4 rounded-lg border border-dashed bg-muted/20 px-4 py-3">
      <Avatar>
        <AvatarFallback className="bg-muted text-muted-foreground">
          <Mail className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold truncate">
            {invitation.email}
          </span>
          <Badge
            variant="outline"
            className="text-[10px] uppercase tracking-wide"
          >
            {t("pending")}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {role?.name ?? t("noRole")} · {formatExpiry(invitation.expiresAt)}
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          aria-label={t("copyAria", { email: invitation.email })}
          className="gap-1.5"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4" />
              {t("copied")}
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" />
              {t("copyLink")}
            </>
          )}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onCancel(invitation.uuid)}
          disabled={!canCancel}
          aria-label={t("cancelAria", { email: invitation.email })}
          className="gap-1.5"
        >
          <X className="h-4 w-4" />
          {t("cancel")}
        </Button>
      </div>
    </div>
  );
}
