"use client";

import { X } from "lucide-react";
import { PERMISSIONS_CATALOG } from "@/src/domain/constants/permissions-catalog";
import { Badge } from "@/src/presentation/components/ui/badge";

interface SelectedPermissionsProps {
  permissions: string[];
  onRemove?: (code: string) => void;
  readonly?: boolean;
}

export function SelectedPermissions({
  permissions,
  onRemove,
  readonly = false,
}: SelectedPermissionsProps) {
  if (permissions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No hay permisos seleccionados
      </p>
    );
  }

  const grouped = PERMISSIONS_CATALOG.map((cat) => ({
    ...cat,
    selected: cat.permissions.filter((p) => permissions.includes(p.code)),
  })).filter((cat) => cat.selected.length > 0);

  return (
    <div className="space-y-3">
      {grouped.map((cat) => (
        <div key={cat.id}>
          <p className="text-xs font-medium text-muted-foreground mb-1.5">
            {cat.label}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {cat.selected.map((perm) => (
              <Badge
                key={perm.code}
                variant="secondary"
                className="gap-1 text-xs"
              >
                {perm.label}
                {!readonly && onRemove && (
                  <button
                    type="button"
                    onClick={() => onRemove(perm.code)}
                    className="ml-0.5 hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </Badge>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
