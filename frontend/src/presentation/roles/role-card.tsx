"use client";

import { Pencil, Shield, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { usePermissions } from "@/src/application/hooks/use-permissions";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import { TenantRoleStatus } from "@/src/domain/enums/tenants";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";

interface RoleCardProps {
  role: TenantRole;
  onEdit: (uuid: string) => void;
  onDelete: (uuid: string) => void;
}

export function RoleCard({ role, onEdit, onDelete }: RoleCardProps) {
  const t = useTranslations("RoleCard");
  const { hasPermission } = usePermissions();
  const canUpdate = hasPermission("tenant_roles.update");
  const canDelete = hasPermission("tenant_roles.delete");

  return (
    <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted">
        <Shield className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold truncate">{role.name}</h3>
        <div className="flex items-center gap-2 mt-1.5">
          <Badge
            variant={
              role.status === TenantRoleStatus.ACTIVE ? "default" : "secondary"
            }
          >
            {role.status === TenantRoleStatus.ACTIVE
              ? t("active")
              : t("inactive")}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {t("permissions", { count: role.permissions.length })}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={() => onEdit(role.uuid)}
          disabled={!canUpdate}
        >
          <Pencil className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={() => onDelete(role.uuid)}
          disabled={!canDelete}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
