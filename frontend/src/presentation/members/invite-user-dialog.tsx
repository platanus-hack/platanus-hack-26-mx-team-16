"use client";

import { ArrowLeft, ArrowRight, Check, Mail, Shield } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type { InviteMemberPayload } from "@/src/domain/repositories/tenant-user";
import { Button } from "@/src/presentation/components/ui/button";
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
import { ActionButton } from "@/src/presentation/components/ui/action-button";

interface InviteUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: InviteMemberPayload) => Promise<void>;
  roles: TenantRole[];
}

export function InviteUserDialog({
  open,
  onOpenChange,
  onSubmit,
  roles,
}: InviteUserDialogProps) {
  const t = useTranslations("InviteUserDialog");
  const [step, setStep] = useState(0);
  const [email, setEmail] = useState("");
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const steps = [
    { label: t("stepEmail"), icon: Mail },
    { label: t("stepRole"), icon: Shield },
    { label: t("stepConfirm"), icon: Check },
  ] as const;

  const selectedRole = roles.find((r) => r.uuid === selectedRoleId);

  const canNext =
    step === 0 ? email.trim().length > 0 : step === 1 ? !!selectedRole : true;

  const resetForm = () => {
    setStep(0);
    setEmail("");
    setSelectedRoleId("");
  };

  const handleOpenChange = (value: boolean) => {
    if (!value) resetForm();
    onOpenChange(value);
  };

  const handleSubmit = async () => {
    if (!selectedRole) return;
    setIsSubmitting(true);
    try {
      await onSubmit({
        email: email.trim(),
        roleSlug: selectedRole.slug,
      });
      resetForm();
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-lg p-6">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>
            {step === 0 && t("step1Description")}
            {step === 1 && t("step2Description")}
            {step === 2 && t("step3Description")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2 mt-4 mb-6">
          {steps.map((s, i) => {
            const Icon = s.icon;
            const isActive = i === step;
            const isDone = i < step;
            return (
              <div key={s.label} className="flex items-center gap-2 flex-1">
                <div
                  className={`flex items-center justify-center h-8 w-8 rounded-full shrink-0 text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : isDone
                        ? "bg-primary/20 text-primary"
                        : "bg-muted text-muted-foreground"
                  }`}
                >
                  {isDone ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <span
                  className={`text-xs font-medium hidden sm:block ${
                    isActive ? "text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {s.label}
                </span>
                {i < steps.length - 1 && (
                  <div
                    className={`flex-1 h-px ${
                      isDone ? "bg-primary/40" : "bg-border"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>

        {step === 0 && (
          <div className="space-y-2">
            <Label htmlFor="invite-email">{t("emailLabel")}</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder={t("emailPlaceholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
            />
            <p className="text-[11px] text-muted-foreground">
              {t("emailHint")}
            </p>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-2">
            {roles.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                {t("noRoles")}
              </p>
            ) : (
              <div className="grid gap-2">
                {roles.map((role) => {
                  const isSelected = selectedRoleId === role.uuid;
                  return (
                    <button
                      key={role.uuid}
                      type="button"
                      onClick={() => setSelectedRoleId(role.uuid)}
                      className={`flex items-center gap-3 rounded-lg border p-3 text-left transition-colors ${
                        isSelected
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/30 hover:bg-muted/50"
                      }`}
                    >
                      <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${
                          isSelected ? "bg-primary/10" : "bg-muted"
                        }`}
                      >
                        <Shield
                          className={`h-4 w-4 ${
                            isSelected
                              ? "text-primary"
                              : "text-muted-foreground"
                          }`}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{role.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {t("permissions", {
                            count: role.permissions.length,
                          })}
                        </p>
                      </div>
                      {isSelected && (
                        <Check className="h-4 w-4 text-primary shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Mail className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold">{email}</p>
                <p className="text-xs text-muted-foreground">
                  {t("invitationSummary")}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                {t("rolePrefix")}{" "}
                <strong>{selectedRole?.name || t("noRole")}</strong>
              </span>
            </div>
          </div>
        )}

        <div className="flex justify-between mt-6">
          <Button
            variant="outline"
            onClick={() =>
              step === 0 ? handleOpenChange(false) : setStep(step - 1)
            }
            disabled={isSubmitting}
          >
            {step === 0 ? (
              t("cancel")
            ) : (
              <>
                <ArrowLeft className="h-4 w-4 mr-1" />
                {t("back")}
              </>
            )}
          </Button>

          {step < 2 ? (
            <Button onClick={() => setStep(step + 1)} disabled={!canNext}>
              {t("next")}
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <ActionButton onClick={handleSubmit} loading={isSubmitting}>
              {t("sendInvitation")}
            </ActionButton>
          )}
        </div>
      </DialogPopup>
    </Dialog>
  );
}
