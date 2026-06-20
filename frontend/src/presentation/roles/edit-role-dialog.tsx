"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import { TenantRoleStatus } from "@/src/domain/enums/tenants";
import type { UpdateTenantRolePayload } from "@/src/domain/repositories/tenant-role";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { PermissionSelector } from "./permission-selector";
import { SelectedPermissions } from "./selected-permissions";

interface EditRoleDialogProps {
  role: TenantRole | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (uuid: string, payload: UpdateTenantRolePayload) => Promise<void>;
}

export function EditRoleDialog({
  role,
  open,
  onOpenChange,
  onSubmit,
}: EditRoleDialogProps) {
  const t = useTranslations("RoleDialog");
  const [name, setName] = useState("");
  const [status, setStatus] = useState<TenantRoleStatus>(
    TenantRoleStatus.ACTIVE
  );
  const [permissions, setPermissions] = useState<string[]>([]);
  const [showPermissionSelector, setShowPermissionSelector] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (role) {
      setName(role.name);
      setStatus(role.status);
      setPermissions(role.permissions.map((p) => p.code));
    }
  }, [role]);

  const canSubmit = name.trim().length > 0 && !isSubmitting;

  const handleSubmit = async () => {
    if (!canSubmit || !role) return;
    setIsSubmitting(true);
    try {
      await onSubmit(role.uuid, {
        name: name.trim(),
        permissions,
        status,
      });
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemovePermission = (code: string) => {
    setPermissions((prev) => prev.filter((c) => c !== code));
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogBackdrop />
        <DialogPopup className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle>{t("editTitle")}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="edit-role-name">{t("nameLabel")}</Label>
              <Input
                id="edit-role-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSubmit();
                }}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label>{t("status")}</Label>
              <Select
                value={status}
                onValueChange={(val) => setStatus(val as TenantRoleStatus)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TenantRoleStatus.ACTIVE}>
                    {t("statusActive")}
                  </SelectItem>
                  <SelectItem value={TenantRoleStatus.INACTIVE}>
                    {t("statusInactive")}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t("permissions")}</Label>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowPermissionSelector(true)}
                type="button"
              >
                {t("selectPermissions")}
              </Button>
              <div className="mt-2">
                <SelectedPermissions
                  permissions={permissions}
                  onRemove={handleRemovePermission}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              {t("cancel")}
            </Button>
            <ActionButton
              onClick={handleSubmit}
              disabled={!canSubmit}
              loading={isSubmitting}
            >
              {t("save")}
            </ActionButton>
          </DialogFooter>
        </DialogPopup>
      </Dialog>

      <PermissionSelector
        open={showPermissionSelector}
        onOpenChange={setShowPermissionSelector}
        selected={permissions}
        onConfirm={setPermissions}
      />
    </>
  );
}
