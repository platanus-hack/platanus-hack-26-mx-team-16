/**
 * ScanForm (§F5) — the universal entry point: URL + level + attestation gate.
 * The legal control expressed as UI. Used by the `/scan` page AND mounted as a
 * modal from `/` (Hall of Shame CTA).
 *
 * Behavior:
 *  - zod-validated (scanFormSchema) via react-hook-form. Normalizes the URL and
 *    previews the detected host ("Vas a escanear: sat.gob.mx").
 *  - 3 level cards (radio): basico (default, passive) · intermedio · avanzado.
 *  - <AttestationGate> renders ONLY for active levels (intermedio/avanzado).
 *    In basico it is hidden and `authorized=false`. The gate already does the
 *    .gob.mx red reinforcement + the terms Dialog.
 *  - Submit is disabled while pending (no double-submit) and while an active
 *    level is unattested.
 *  - POST /api/owliver/scans → { scanId } → redirect /scans/[id]. Error mapping:
 *    422 attestation/validation → inline; 429 Retry-After → inline; 403 → toast
 *    (here surfaced as an inline destructive banner — no sonner dep yet).
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, Loader2, Search, ShieldCheck, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useMemo } from "react";
import { Controller, useForm } from "react-hook-form";

import { cn } from "@/src/application/lib/utils";
import {
  type CreateScanError,
  useCreateScan,
} from "@/src/application/owliver/hooks/use-create-scan";
import { firstErrorMessage } from "@/src/application/owliver/lib/envelope";
import { extractHost, normalizeUrl } from "@/src/application/owliver/lib/url";
import type { ScanLevel } from "@/src/application/owliver/schemas/api";
import {
  type ScanFormInput,
  type ScanFormValues,
  scanFormSchema,
} from "@/src/application/owliver/schemas/scan-form";
import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";
import { AttestationGate } from "@/src/presentation/owliver/scan/attestation-gate";

type LevelOption = {
  value: ScanLevel;
  label: string;
  blurb: string;
  icon: typeof ShieldCheck;
  active: boolean;
};

const LEVELS: LevelOption[] = [
  {
    value: "basico",
    label: "Básico",
    blurb: "Pasivo, no intrusivo, anónimo. Sin permisos.",
    icon: ShieldCheck,
    active: false,
  },
  {
    value: "intermedio",
    label: "Intermedio",
    blurb: "Activo suave, con límites de velocidad.",
    icon: Zap,
    active: true,
  },
  {
    value: "avanzado",
    label: "Avanzado",
    blurb: "Explotación. Requiere autorización.",
    icon: Lock,
    active: true,
  },
];

export type ScanFormProps = {
  /** Called after a successful create + redirect (e.g. to close a modal). */
  onSuccess?: (scanId: string) => void;
  /** Seeds the URL field (e.g. the `/scan?url=<host>` deep link). */
  initialUrl?: string;
  className?: string;
};

/** Map a CreateScanError to a human es-MX message (422/429/403/other). */
function mapSubmitError(err: CreateScanError): string {
  if (err.status === 429) {
    const secs = err.retryAfter;
    return secs && secs > 0
      ? `Demasiados escaneos. Intenta de nuevo en ${secs}s.`
      : "Demasiados escaneos. Intenta de nuevo en un momento.";
  }
  if (err.status === 403) {
    return firstErrorMessage(
      err.body,
      "No tienes permiso para escanear este dominio."
    );
  }
  if (err.status === 422) {
    return firstErrorMessage(
      err.body,
      "No pudimos validar la solicitud. Revisa la URL y la autorización."
    );
  }
  return firstErrorMessage(err.body, "Ocurrió un error al iniciar el escaneo.");
}

export function ScanForm({ onSuccess, initialUrl, className }: ScanFormProps) {
  const router = useRouter();
  const createScan = useCreateScan();
  const fieldId = useId();

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ScanFormInput, unknown, ScanFormValues>({
    resolver: zodResolver(scanFormSchema),
    defaultValues: { url: initialUrl ?? "", level: "basico", authorized: false },
    mode: "onSubmit",
  });

  const url = watch("url") ?? "";
  const level = watch("level") ?? "basico";
  const authorized = watch("authorized") ?? false;

  const host = useMemo(() => extractHost(url), [url]);
  const isActive = level !== "basico";
  const submitError = createScan.error ? mapSubmitError(createScan.error) : null;

  // Disable submit on: in-flight request, or active level without attestation.
  const submitDisabled = createScan.isPending || (isActive && !authorized);

  const onSubmit = handleSubmit((values) => {
    // Normalize before sending; the schema already guaranteed parseability.
    const normalized = normalizeUrl(values.url);
    const finalUrl = normalized ? normalized.toString() : values.url;
    createScan.mutate(
      {
        url: finalUrl,
        level: values.level,
        // basico never attests; active levels carry the checkbox state.
        authorized: values.level === "basico" ? false : values.authorized,
      },
      {
        onSuccess: ({ scanId }) => {
          onSuccess?.(scanId);
          router.push(`/scans/${scanId}`);
        },
      }
    );
  });

  return (
    <form onSubmit={onSubmit} className={cn("space-y-6", className)} noValidate>
      {/* URL field */}
      <div className="space-y-2">
        <label
          htmlFor={`${fieldId}-url`}
          className="block text-sm font-medium text-foreground"
        >
          URL del sitio a auditar
        </label>
        <Controller
          control={control}
          name="url"
          render={({ field }) => (
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-on-surface-variant"
                aria-hidden
              />
              <Input
                {...field}
                id={`${fieldId}-url`}
                type="text"
                inputMode="url"
                autoComplete="url"
                placeholder="sat.gob.mx"
                aria-invalid={!!errors.url}
                aria-describedby={host ? `${fieldId}-host` : undefined}
                className="h-12 pl-11 text-base"
              />
            </div>
          )}
        />
        {errors.url ? (
          <p className="text-xs font-medium text-destructive">
            {errors.url.message}
          </p>
        ) : host ? (
          <p
            id={`${fieldId}-host`}
            className="text-xs text-on-surface-variant"
          >
            Vas a escanear:{" "}
            <span className="font-mono font-medium text-foreground">
              {host}
            </span>
          </p>
        ) : null}
      </div>

      {/* Level selector (3 radio cards) */}
      <Controller
        control={control}
        name="level"
        render={({ field }) => (
          <fieldset className="space-y-2">
            <legend className="mb-2 block text-sm font-medium text-foreground">
              Nivel de auditoría
            </legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {LEVELS.map((opt) => {
                const selected = field.value === opt.value;
                const Icon = opt.icon;
                return (
                  <label
                    key={opt.value}
                    className={cn(
                      "relative flex cursor-pointer flex-col gap-1.5 rounded-2xl border p-3.5 transition-colors",
                      selected
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : "border-outline-variant bg-card hover:bg-surface-container-low"
                    )}
                  >
                    <input
                      type="radio"
                      name={field.name}
                      value={opt.value}
                      checked={selected}
                      onChange={() => {
                        field.onChange(opt.value);
                        // Reset attestation when switching to/within levels so a
                        // stale `true` never leaks across a level change.
                        if (opt.value === "basico") {
                          setValue("authorized", false);
                        }
                      }}
                      className="sr-only"
                    />
                    <div className="flex items-center gap-2">
                      <Icon
                        className={cn(
                          "size-4",
                          selected ? "text-primary" : "text-on-surface-variant"
                        )}
                        aria-hidden
                      />
                      <span className="text-sm font-semibold text-foreground">
                        {opt.label}
                      </span>
                      {opt.active && (
                        <span className="ml-auto rounded-full bg-tertiary/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-tertiary">
                          activo
                        </span>
                      )}
                    </div>
                    <span className="text-xs leading-snug text-on-surface-variant">
                      {opt.blurb}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        )}
      />

      {/* Attestation gate — active levels ONLY */}
      {isActive && (
        <Controller
          control={control}
          name="authorized"
          render={({ field }) => (
            <AttestationGate
              host={host}
              checked={field.value ?? false}
              onCheckedChange={field.onChange}
              error={errors.authorized?.message}
            />
          )}
        />
      )}

      {/* Submit-level error (422 / 429 / 403 / other) */}
      {submitError && (
        <p
          role="alert"
          className="rounded-xl border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm font-medium text-destructive-deep"
        >
          {submitError}
        </p>
      )}

      <Button
        type="submit"
        variant="tertiary"
        size="lg"
        disabled={submitDisabled}
        className="w-full"
      >
        {createScan.isPending ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Iniciando escaneo…
          </>
        ) : (
          "Auditar este sitio →"
        )}
      </Button>
    </form>
  );
}
