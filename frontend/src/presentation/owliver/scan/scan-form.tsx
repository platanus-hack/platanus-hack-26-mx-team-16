/**
 * ScanForm (§F5) — the universal entry point: URL + level + attestation gate.
 * The legal control expressed as UI. Used by the `/scan` page AND mounted as a
 * modal from `/` (Hall of Shame CTA).
 *
 * State lives in a per-instance zustand store (`createScanFormStore`) provided
 * through context. Each field subscribes to ONLY its own slice, so typing in
 * the URL field re-renders that field alone — not the level cards, attestation
 * gate, or submit button. This is what fixes the "type → page re-renders →
 * input loses focus" bug the controlled react-hook-form + `watch()` setup had.
 *
 * Behavior:
 *  - zod-validated (scanFormSchema) on submit via the store's `validate()`.
 *    Normalizes the URL and previews the detected host ("Vas a escanear: …").
 *  - 3 level cards (radio): basico (default, passive) · intermedio · avanzado.
 *  - <AttestationGate> renders ONLY for active levels (intermedio/avanzado).
 *    In basico it is hidden and `authorized=false`.
 *  - Submit is disabled while pending (no double-submit) and while an active
 *    level is unattested.
 *  - POST /api/owliver/scans → { scanId } → redirect /scans/[id]. Error mapping:
 *    422 attestation/validation → inline; 429 Retry-After → inline; 403 → inline.
 */
"use client";

import { Loader2, Lock, Search, ShieldCheck, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useMemo, useState } from "react";

import { cn } from "@/src/application/lib/utils";
import {
  type CreateScanError,
  useCreateScan,
} from "@/src/application/owliver/hooks/use-create-scan";
import { firstErrorMessage } from "@/src/application/owliver/lib/envelope";
import { extractHost } from "@/src/application/owliver/lib/url";
import type { ScanLevel } from "@/src/application/owliver/schemas/api";
import {
  createScanFormStore,
  ScanFormStoreContext,
  useScanFormStore,
  useScanFormStoreApi,
} from "@/src/application/owliver/stores/scan-form-store";
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
  // Lazy, per-instance store init (rerender-lazy-state-init). Isolates the
  // `/scan` page form from the modal form so neither leaks into the other.
  const [store] = useState(() => createScanFormStore(initialUrl ?? ""));

  return (
    <ScanFormStoreContext.Provider value={store}>
      <ScanFormFields onSuccess={onSuccess} className={className} />
    </ScanFormStoreContext.Provider>
  );
}

function ScanFormFields({
  onSuccess,
  className,
}: Pick<ScanFormProps, "onSuccess" | "className">) {
  const router = useRouter();
  const createScan = useCreateScan();
  // Deferred read: the submit handler reads the store without subscribing, so
  // typing never re-renders this wrapper (rerender-defer-reads).
  const store = useScanFormStoreApi();

  const submitError = createScan.error
    ? mapSubmitError(createScan.error)
    : null;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (createScan.isPending) return;
    const body = store.getState().validate();
    if (!body) return;
    createScan.mutate(body, {
      onSuccess: ({ scanId }) => {
        onSuccess?.(scanId);
        router.push(`/scans/${scanId}`);
      },
    });
  };

  return (
    <form onSubmit={onSubmit} className={cn("space-y-6", className)} noValidate>
      <UrlField />
      <LevelSelector />
      <AttestationField />

      {/* Submit-level error (422 / 429 / 403 / other) */}
      {submitError && (
        <p
          role="alert"
          className="rounded-xl border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm font-medium text-destructive-deep"
        >
          {submitError}
        </p>
      )}

      <SubmitButton pending={createScan.isPending} />
    </form>
  );
}

function UrlField() {
  const fieldId = useId();
  const url = useScanFormStore((s) => s.url);
  const error = useScanFormStore((s) => s.errors.url);
  const setUrl = useScanFormStore((s) => s.setUrl);
  const host = useMemo(() => extractHost(url), [url]);

  return (
    <div className="space-y-2">
      <label
        htmlFor={`${fieldId}-url`}
        className="block text-sm font-medium text-foreground"
      >
        URL del sitio a auditar
      </label>
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-on-surface-variant"
          aria-hidden
        />
        <Input
          id={`${fieldId}-url`}
          name="url"
          type="text"
          inputMode="url"
          autoComplete="url"
          placeholder="example.com"
          value={url}
          // Base UI's controlled API is `onValueChange` (it intercepts the
          // native onChange) — wiring `onChange` here silently drops keystrokes.
          onValueChange={setUrl}
          aria-invalid={!!error}
          aria-describedby={host ? `${fieldId}-host` : undefined}
          className="h-12 pl-11 text-base"
        />
      </div>
      {error ? (
        <p className="text-xs font-medium text-destructive">{error}</p>
      ) : host ? (
        <p id={`${fieldId}-host`} className="text-xs text-on-surface-variant">
          Vas a escanear:{" "}
          <span className="font-mono font-medium text-foreground">{host}</span>
        </p>
      ) : null}
    </div>
  );
}

function LevelSelector() {
  const level = useScanFormStore((s) => s.level);
  const setLevel = useScanFormStore((s) => s.setLevel);

  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 block text-sm font-medium text-foreground">
        Nivel de auditoría
      </legend>
      <div className="grid gap-2 sm:grid-cols-3">
        {LEVELS.map((opt) => {
          const selected = level === opt.value;
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
                name="level"
                value={opt.value}
                checked={selected}
                onChange={() => setLevel(opt.value)}
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
  );
}

/**
 * Gate: subscribes ONLY to the active/inactive boolean so a URL keystroke never
 * re-renders it in `basico`. The inner component (mounted only for active
 * levels) owns the host + attestation subscriptions.
 */
function AttestationField() {
  const isActive = useScanFormStore((s) => s.level !== "basico");
  if (!isActive) return null;
  return <ActiveAttestation />;
}

function ActiveAttestation() {
  const host = useScanFormStore((s) => extractHost(s.url));
  const checked = useScanFormStore((s) => s.authorized);
  const error = useScanFormStore((s) => s.errors.authorized);
  const setAuthorized = useScanFormStore((s) => s.setAuthorized);

  return (
    <AttestationGate
      host={host}
      checked={checked}
      onCheckedChange={setAuthorized}
      error={error}
    />
  );
}

function SubmitButton({ pending }: { pending: boolean }) {
  // Subscribe to a DERIVED boolean, not raw level/authorized values
  // (rerender-derived-state), so this button only re-renders when its disabled
  // state actually flips.
  const blockedByAttestation = useScanFormStore(
    (s) => s.level !== "basico" && !s.authorized
  );

  return (
    <Button
      type="submit"
      variant="tertiary"
      size="lg"
      disabled={pending || blockedByAttestation}
      className="w-full"
    >
      {pending ? (
        <>
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Iniciando escaneo…
        </>
      ) : (
        "Auditar este sitio →"
      )}
    </Button>
  );
}
