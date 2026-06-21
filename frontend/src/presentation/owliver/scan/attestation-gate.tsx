/**
 * AttestationGate (§F5) — the legal control rendered as UI. The scan form mounts
 * this ONLY for active levels (intermedio/avanzado); in `basico` it is not
 * rendered and `authorized=false`. Controlled: the form owns `checked` and the
 * submit-disabled logic (this just renders the warning + checkbox + terms).
 *
 * Rules surfaced here (01-legal-ethics §2.4):
 *  - Prominent warning naming the target host.
 *  - Mandatory checkbox: "Declaro tener autorización…" — without it the form
 *    keeps submit disabled.
 *  - "Ver términos" opens a Dialog.
 */
"use client";

import { ShieldAlert } from "lucide-react";

import { cn } from "@/src/application/lib/utils";
import { Checkbox } from "@/src/presentation/components/ui/checkbox";
import {
  Dialog,
  DialogBody,
  DialogPopup,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/src/presentation/components/ui/dialog";

export type AttestationGateProps = {
  /** Detected target host (drives the warning copy). */
  host: string | null;
  /** Attestation checkbox state (owned by the form). */
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  /** Inline error (e.g. zod "must attest" when submitted unchecked). */
  error?: string;
  className?: string;
};

export function AttestationGate({
  host,
  checked,
  onCheckedChange,
  error,
  className,
}: AttestationGateProps) {
  const target = host ?? "este dominio";

  return (
    <div
      data-slot="attestation-gate"
      className={cn(
        "space-y-3 rounded-2xl border border-destructive/40 bg-destructive/5 p-4",
        className
      )}
    >
      <div className="flex items-start gap-2.5">
        <ShieldAlert className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden />
        <p className="text-sm font-medium text-foreground">
          Vas a lanzar pruebas intrusivas contra{" "}
          <span className="font-mono font-semibold">{target}</span>; hacerlo sin
          autorización es ilegal.
        </p>
      </div>

      <label className="flex cursor-pointer items-start gap-2.5">
        <Checkbox
          checked={checked}
          onCheckedChange={(v) => onCheckedChange(v === true)}
          aria-invalid={!!error}
          className="mt-0.5"
        />
        <span className="text-sm text-foreground">
          Declaro tener autorización para auditar este dominio.{" "}
          <span className="text-on-surface-variant">
            Esta autorización quedará registrada a tu nombre y con fecha.
          </span>
        </span>
      </label>

      <div className="flex items-center justify-between gap-3">
        {error ? (
          <span className="text-xs font-medium text-destructive">{error}</span>
        ) : (
          <span />
        )}
        <Dialog>
          <DialogTrigger className="text-xs font-medium text-primary underline-offset-2 hover:underline">
            Ver términos
          </DialogTrigger>
          <DialogPopup className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Términos de autorización de auditoría</DialogTitle>
            </DialogHeader>
            <DialogBody className="space-y-3 text-sm text-on-surface-variant">
              <p>
                Al continuar, declaras bajo tu responsabilidad que cuentas con
                autorización legítima del propietario del dominio para ejecutar
                pruebas de seguridad activas.
              </p>
              <p>
                Owliver registra <span className="font-mono">authorized_at</span>{" "}
                y <span className="font-mono">requested_by</span> de cada
                escaneo activo. El uso no autorizado de pruebas intrusivas puede
                constituir un delito conforme a la legislación aplicable.
              </p>
              <p>
                Los resultados de escaneos activos son privados de tu cuenta y no
                se publican en el ranking público.
              </p>
            </DialogBody>
          </DialogPopup>
        </Dialog>
      </div>
    </div>
  );
}
