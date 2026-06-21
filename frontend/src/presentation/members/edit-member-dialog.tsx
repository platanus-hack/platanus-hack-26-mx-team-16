"use client";

import { Camera } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { useSessionStore } from "@/src/application/contexts/session-store";
import { useUploadMemberPhotoMutation } from "@/src/application/hooks/queries/members";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type { TenantUser } from "@/src/domain/entities/tenants/tenant-user";
import type { UpdateTenantUserPayload } from "@/src/domain/repositories/tenant-user";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/src/presentation/components/ui/avatar";
import { Button } from "@/src/presentation/components/ui/button";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import {
  Dialog,
  DialogBackdrop,
  DialogDescription,
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
import { Spinner } from "@/src/presentation/components/ui/spinner";
import { Switch } from "@/src/presentation/components/ui/switch";

interface EditMemberDialogProps {
  member: TenantUser | null;
  roles: TenantRole[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (uuid: string, payload: UpdateTenantUserPayload) => Promise<void>;
  canEditRole: boolean;
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

export function EditMemberDialog({
  member,
  roles,
  open,
  onOpenChange,
  onSubmit,
  canEditRole,
}: EditMemberDialogProps) {
  const t = useTranslations("EditMemberDialog");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [tenantRoleId, setTenantRoleId] = useState("");
  const [status, setStatus] = useState<string>("ACTIVE");
  const [isSupport, setIsSupport] = useState(false);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSuperuser = useSessionStore((s) => s.user?.isSuperuser === true);
  const uploadPhoto = useUploadMemberPhotoMutation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const statusOptions = [
    { value: "ACTIVE", label: t("statusOptions.active") },
    { value: "PENDING", label: t("statusOptions.pending") },
    { value: "INACTIVE", label: t("statusOptions.inactive") },
  ];

  useEffect(() => {
    if (!member) return;
    setFirstName(member.firstName ?? "");
    setLastName(member.lastName ?? "");
    setEmail(member.emailAddress?.email ?? "");
    setTenantRoleId(member.tenantRole?.uuid ?? "");
    setStatus(member.status || "ACTIVE");
    setIsSupport(member.isSupport ?? false);
    setPhotoUrl(member.photoUrl ?? null);
    setError(null);
  }, [member]);

  if (!member) return null;

  const handlePhotoPick = () => fileInputRef.current?.click();

  const handlePhotoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError(null);
    try {
      const updated = await uploadPhoto.mutateAsync({
        uuid: member.uuid,
        file,
      });
      setPhotoUrl(updated.photoUrl ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("uploadError"));
    }
  };

  const handleSubmit = async () => {
    const payload: UpdateTenantUserPayload = {};
    const trimmedFirst = firstName.trim();
    const trimmedLast = lastName.trim();
    const trimmedEmail = email.trim();

    if (trimmedFirst !== (member.firstName ?? ""))
      payload.firstName = trimmedFirst;
    if (trimmedLast !== (member.lastName ?? "")) payload.lastName = trimmedLast;
    if (trimmedEmail !== (member.emailAddress?.email ?? ""))
      payload.email = trimmedEmail;
    if (
      canEditRole &&
      !member.isOwner &&
      tenantRoleId &&
      tenantRoleId !== member.tenantRole?.uuid
    ) {
      payload.tenantRoleId = tenantRoleId;
    }
    if (status !== member.status) payload.status = status;
    if (isSuperuser && isSupport !== (member.isSupport ?? false)) {
      payload.isSupport = isSupport;
    }

    if (Object.keys(payload).length === 0) {
      onOpenChange(false);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(member.uuid, payload);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("saveError"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const isUploadingPhoto = uploadPhoto.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-md p-6">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 mt-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Avatar className="h-16 w-16">
                {photoUrl && <AvatarImage src={photoUrl} alt={t("photoAlt")} />}
                <AvatarFallback className="bg-primary text-primary-foreground text-base">
                  {getInitials(firstName, lastName)}
                </AvatarFallback>
              </Avatar>
              {isUploadingPhoto && (
                <div className="absolute inset-0 grid place-items-center rounded-full bg-background/70">
                  <Spinner size="sm" />
                </div>
              )}
            </div>
            <div className="flex flex-col items-start gap-1">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handlePhotoPick}
                disabled={isUploadingPhoto}
                className="gap-2"
              >
                <Camera className="h-4 w-4" />
                {photoUrl ? t("changePhoto") : t("uploadPhoto")}
              </Button>
              <p className="text-[11px] text-muted-foreground">
                {t("photoHint")}
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handlePhotoChange}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="edit-first-name">{t("firstName")}</Label>
              <Input
                id="edit-first-name"
                value={firstName}
                onValueChange={setFirstName}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-last-name">{t("lastName")}</Label>
              <Input
                id="edit-last-name"
                value={lastName}
                onValueChange={setLastName}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-email">{t("email")}</Label>
            <Input
              id="edit-email"
              type="email"
              value={email}
              onValueChange={setEmail}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="edit-status">{t("status")}</Label>
              <Select
                value={status}
                onValueChange={(val) => val && setStatus(val)}
              >
                <SelectTrigger id="edit-status" className="w-full">
                  <SelectValue placeholder={t("status")}>
                    {statusOptions.find((s) => s.value === status)?.label ??
                      status}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {statusOptions.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {!member.isOwner && (
              <div className="space-y-2">
                <Label htmlFor="edit-role">{t("role")}</Label>
                <Select
                  value={tenantRoleId}
                  onValueChange={(val) => setTenantRoleId(val ?? "")}
                  disabled={!canEditRole}
                >
                  <SelectTrigger id="edit-role" className="w-full">
                    <SelectValue placeholder={t("noRole")}>
                      {roles.find((r) => r.uuid === tenantRoleId)?.name ??
                        t("noRole")}
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
              </div>
            )}
          </div>

          {isSuperuser && (
            <div className="flex items-start justify-between gap-3 rounded-md border border-dashed border-border bg-muted/30 p-3">
              <div className="flex flex-col gap-0.5">
                <Label htmlFor="edit-is-support" className="text-sm">
                  {t("support")}
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  {t("supportHint")}
                </p>
              </div>
              <Switch
                id="edit-is-support"
                checked={isSupport}
                onCheckedChange={(v) => setIsSupport(Boolean(v))}
              />
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            {t("cancel")}
          </Button>
          <ActionButton onClick={handleSubmit} loading={isSubmitting}>
            {t("save")}
          </ActionButton>
        </div>
      </DialogPopup>
    </Dialog>
  );
}
