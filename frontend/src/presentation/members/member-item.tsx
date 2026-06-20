"use client";

import { Crown, KeyRound, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { usePermissions } from "@/src/application/hooks/use-permissions";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type { TenantUser } from "@/src/domain/entities/tenants/tenant-user";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/src/presentation/components/ui/avatar";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/src/presentation/components/ui/tooltip";

const TOOLTIP_HOVER_DELAY_MS = 500;

interface MemberItemProps {
  member: TenantUser;
  roles: TenantRole[];
  onRoleChange: (uuid: string, roleId: string) => void;
  onRemove: (uuid: string) => void;
  onSendResetPassword: (tenantUserId: string, email: string) => void;
  onEdit: (uuid: string) => void;
}

function getInitials(
  firstName: string | null,
  lastName: string | null
): string {
  const parts = [firstName, lastName].filter(Boolean);
  if (parts.length === 0) return "?";
  return parts
    .map((n) => n![0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function MemberItem({
  member,
  roles,
  onRoleChange,
  onRemove,
  onSendResetPassword,
  onEdit,
}: MemberItemProps) {
  const t = useTranslations("MemberItem");
  const currentRoleId = member.tenantRole?.uuid || "";
  const { hasPermission } = usePermissions();
  const canUpdate = hasPermission("tenant_users.update");
  const canDelete = hasPermission("tenant_users.delete");
  const memberEmail = member.emailAddress?.email;
  const canSendReset = !!memberEmail && hasPermission("tenant_users.update");

  const getDisplayName = (m: TenantUser): string => {
    const parts = [m.firstName, m.lastName].filter(Boolean);
    if (parts.length > 0) return parts.join(" ");
    return m.emailAddress?.email || t("noName");
  };

  const displayName = getDisplayName(member);

  const handleCardClick = () => {
    if (canUpdate) onEdit(member.uuid);
  };

  const handleCardKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (!canUpdate) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onEdit(member.uuid);
    }
  };

  const stop = (e: React.SyntheticEvent) => e.stopPropagation();

  return (
    <div
      role={canUpdate ? "button" : undefined}
      tabIndex={canUpdate ? 0 : undefined}
      onClick={canUpdate ? handleCardClick : undefined}
      onKeyDown={canUpdate ? handleCardKeyDown : undefined}
      aria-label={canUpdate ? t("editAria", { name: displayName }) : undefined}
      className={`flex items-center gap-4 rounded-lg border bg-card px-4 py-3 transition-colors ${
        canUpdate
          ? "cursor-pointer hover:bg-muted/40 focus-visible:outline-2 focus-visible:outline-ring"
          : ""
      }`}
    >
      <Avatar>
        {member.photoUrl && (
          <AvatarImage src={member.photoUrl} alt={displayName} />
        )}
        <AvatarFallback className="bg-primary text-primary-foreground">
          {getInitials(member.firstName, member.lastName)}
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold truncate">{displayName}</span>
          {member.isOwner && (
            <Badge variant="outline" className="gap-1 text-xs">
              <Crown className="h-3 w-3" />
              {t("owner")}
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground truncate">{memberEmail}</p>
      </div>

      <div
        className="flex items-center gap-2 shrink-0"
        onClick={stop}
        onKeyDown={stop}
      >
        {member.isOwner ? (
          <Badge variant="secondary" className="text-xs">
            {t("ownerBadge")}
          </Badge>
        ) : (
          <Select
            value={currentRoleId}
            onValueChange={(val) => {
              if (val) onRoleChange(member.uuid, val);
            }}
            disabled={!canUpdate}
          >
            <SelectTrigger className="w-35" size="sm">
              <SelectValue placeholder={t("noRole")}>
                {member.tenantRole?.name || t("noRole")}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {roles.map((role) => (
                <SelectItem key={role.uuid} value={role.uuid}>
                  {role.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <Tooltip delay={TOOLTIP_HOVER_DELAY_MS}>
          <Button
            variant="ghost"
            size="icon"
            onClick={() =>
              memberEmail && onSendResetPassword(member.uuid, memberEmail)
            }
            disabled={!canSendReset}
            aria-label={t("resetAria", {
              target: memberEmail ?? t("unknownUser"),
            })}
            render={(props) => <TooltipTrigger {...props} />}
          >
            <KeyRound className="h-4 w-4" />
          </Button>
          <TooltipContent>{t("resetTooltip")}</TooltipContent>
        </Tooltip>

        {!member.isOwner && (
          <Tooltip delay={TOOLTIP_HOVER_DELAY_MS}>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onRemove(member.uuid)}
              disabled={!canDelete}
              aria-label={t("removeAria", { name: displayName })}
              render={(props) => <TooltipTrigger {...props} />}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
            <TooltipContent>{t("deleteTooltip")}</TooltipContent>
          </Tooltip>
        )}
      </div>
    </div>
  );
}
