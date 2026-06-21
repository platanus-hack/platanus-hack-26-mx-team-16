"use client";

import { ArrowLeft, ArrowRight, Crown } from "lucide-react";
import { useTransition } from "react";
import {
  useOnboardTenantWizardStore,
  type WizardStep,
} from "@/src/application/stores/onboard-tenant-wizard-store";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogDescription,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { onboardTenant } from "./api";
import { StepInfo } from "./step-info";
import { StepMembers } from "./step-members";
import { StepVerify } from "./step-verify";
import { Stepper } from "./stepper";

const STEPS: Array<{ key: WizardStep; label: string }> = [
  { key: "info", label: "Información" },
  { key: "members", label: "Miembros" },
  { key: "verify", label: "Verificación" },
];

function stepIndex(step: WizardStep): number {
  return STEPS.findIndex((s) => s.key === step);
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function OnboardTenantWizard() {
  const open = useOnboardTenantWizardStore((s) => s.open);
  const step = useOnboardTenantWizardStore((s) => s.step);
  const infoValid = useOnboardTenantWizardStore(
    (s) =>
      s.name.trim().length > 0 &&
      s.countryCode.length > 0 &&
      s.currencyCode.length > 0 &&
      s.timeZone.length > 0
  );
  const membersValid = useOnboardTenantWizardStore((s) =>
    s.members.every((m) => EMAIL_RE.test(m.email.trim()))
  );
  const isSubmitting = useOnboardTenantWizardStore((s) => s.isSubmitting);
  const error = useOnboardTenantWizardStore((s) => s.error);
  const setStep = useOnboardTenantWizardStore((s) => s.setStep);
  const close = useOnboardTenantWizardStore((s) => s.close);
  const beginSubmit = useOnboardTenantWizardStore((s) => s.beginSubmit);
  const setError = useOnboardTenantWizardStore((s) => s.setError);
  const setResult = useOnboardTenantWizardStore((s) => s.setResult);

  const [isPending, startTransition] = useTransition();

  const currentIndex = stepIndex(step);

  const canProceed =
    step === "info" ? infoValid : step === "members" ? true : false;

  const isLastInteractiveStep = step === "members";

  const handleNext = () => {
    if (step === "info") {
      setStep("members");
      return;
    }
    if (step === "members") {
      void handleSubmit();
    }
  };

  const handleBack = () => {
    if (step === "members") setStep("info");
  };

  const handleSubmit = async () => {
    beginSubmit();
    startTransition(async () => {
      try {
        const { name, countryCode, members, skipEmail } =
          useOnboardTenantWizardStore.getState();
        const validEmails = members.filter((m) =>
          EMAIL_RE.test(m.email.trim())
        );
        const data = await onboardTenant({
          name: name.trim(),
          countryCode,
          members: validEmails.map((m) => ({
            email: m.email.trim(),
            roleSlug: m.roleSlug,
          })),
          skipEmail,
        });
        setResult({
          tenantId: data.tenant.uuid,
          tenantName: data.tenant.name,
          tenantSlug: data.tenant.slug,
          invitations: data.invitations.map((inv) => ({
            email: inv.email,
            token: inv.token,
            status: inv.status,
            expiresAt: inv.expiresAt,
          })),
        });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "No se pudo crear el tenant";
        setError(message);
      }
    });
  };

  const inviteBaseUrl =
    typeof window !== "undefined" ? window.location.origin : "";

  return (
    <Dialog open={open} onOpenChange={(o) => (o ? null : close())}>
      <DialogBackdrop />
      <DialogPopup className="max-w-xl p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Crown className="h-4 w-4 text-tertiary" />
            Registrar Tenant
          </DialogTitle>
          <DialogDescription>
            Crea un nuevo cliente, invita a su equipo y verifica que todo quedó
            listo.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          <Stepper current={currentIndex} steps={STEPS} />
        </div>

        <div className="pt-2">
          {step === "info" && <StepInfo />}
          {step === "members" && <StepMembers />}
          {step === "verify" && <StepVerify inviteBaseUrl={inviteBaseUrl} />}
        </div>

        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}

        <div className="flex items-center justify-between gap-2 pt-3 border-t border-border/60">
          <Button
            type="button"
            variant="ghost"
            onClick={step === "info" ? close : handleBack}
            disabled={step === "verify" || isSubmitting || isPending}
            className="gap-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {step === "info" ? "Cancelar" : "Atrás"}
          </Button>

          {step !== "verify" ? (
            <Button
              type="button"
              onClick={handleNext}
              disabled={
                !canProceed ||
                (step === "members" && !membersValid) ||
                isSubmitting ||
                isPending
              }
              className="gap-2"
            >
              {isLastInteractiveStep
                ? isSubmitting || isPending
                  ? "Creando…"
                  : "Crear tenant"
                : "Continuar"}
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          ) : (
            <Button type="button" onClick={close}>
              Listo
            </Button>
          )}
        </div>
      </DialogPopup>
    </Dialog>
  );
}
