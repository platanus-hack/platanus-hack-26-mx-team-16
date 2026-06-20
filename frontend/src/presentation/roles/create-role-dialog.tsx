"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { TenantRoleStatus } from "@/src/domain/enums/tenants";
import type { CreateTenantRolePayload } from "@/src/domain/repositories/tenant-role";
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

interface CreateRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: CreateTenantRolePayload) => Promise<void>;
}

export function CreateRoleDialog({
  open,
  onOpenChange,
  onSubmit,
}: CreateRoleDialogProps) {
  const t = useTranslations("RoleDialog");
  const [name, setName] = useState("");
  const [status, setStatus] = useState<TenantRoleStatus>(
    TenantRoleStatus.ACTIVE
  );
  const [permissions, setPermissions] = useState<string[]>([]);
  const [showPermissionSelector, setShowPermissionSelector] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = name.trim().length > 0 && !isSubmitting;

  const resetForm = () => {
    setName("");
    setStatus(TenantRoleStatus.ACTIVE);
    setPermissions([]);
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      await onSubmit({ name: name.trim(), permissions, status });
      resetForm();
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenChange = (value: boolean) => {
    if (!value) resetForm();
    onOpenChange(value);
  };

  const handleRemovePermission = (code: string) => {
    setPermissions((prev) => prev.filter((c) => c !== code));
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogBackdrop />
        <DialogPopup className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle>{t("createTitle")}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="role-name">{t("nameLabel")}</Label>
              <Input
                id="role-name"
                placeholder={t("namePlaceholder")}
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
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
            >
              {t("cancel")}
            </Button>
            <ActionButton
              onClick={handleSubmit}
              disabled={!canSubmit}
              loading={isSubmitting}
            >
              {t("create")}
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
