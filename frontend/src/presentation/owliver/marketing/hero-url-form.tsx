/**
 * HeroUrlForm — the landing's primary call-to-action: type a URL, get audited.
 *
 * It is a thin, friendly front door to `/scan` (§F5): we normalize the host
 * client-side for a live preview ("Vas a auditar example.com") and to disable
 * obviously-bad submits, then deep-link to `/scan?url=<host>` where the real
 * <ScanForm> + attestation gate live. This is UX only — the SSRF/authorization
 * boundary stays on the backend.
 */
"use client";

import { ArrowRight, Globe } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { cn } from "@/src/application/lib/utils";
import {
  extractHost,
  isLikelyPublicHost,
} from "@/src/application/owliver/lib/url";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";

export function HeroUrlForm({ className }: { className?: string }) {
  const router = useRouter();
  const [value, setValue] = React.useState("");
  const [touched, setTouched] = React.useState(false);

  const host = extractHost(value);
  const valid = isLikelyPublicHost(value);
  const showError = touched && value.trim().length > 0 && !valid;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (!valid || !host) return;
    router.push(`/scan?url=${encodeURIComponent(host)}`);
  }

  return (
    <form onSubmit={submit} className={cn("w-full", className)} noValidate>
      <div
        className={cn(
          "flex items-center gap-1.5 rounded-full border bg-surface-container-lowest p-1.5 shadow-sm transition-colors",
          "focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/30",
          showError ? "border-destructive/60" : "border-outline-variant"
        )}
      >
        <Globe
          aria-hidden
          className="ml-3 size-5 shrink-0 text-on-surface-variant"
        />
        <label htmlFor="hero-url" className="sr-only">
          URL del sitio a auditar
        </label>
        <input
          id="hero-url"
          name="url"
          type="text"
          inputMode="url"
          autoComplete="url"
          spellCheck={false}
          placeholder="tu-sitio.gob.mx"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={() => setTouched(true)}
          aria-invalid={showError}
          aria-describedby="hero-url-hint"
          className="min-w-0 flex-1 bg-transparent px-1 text-base text-foreground outline-none placeholder:text-on-surface-variant/70"
        />
        <button
          type="submit"
          className={cn(
            buttonVariants({ variant: "default", size: "lg" }),
            "shrink-0 max-sm:px-4"
          )}
        >
          <span className="max-sm:sr-only">Auditar</span>
          <ArrowRight className="size-4" />
        </button>
      </div>

      <p
        id="hero-url-hint"
        aria-live="polite"
        className={cn(
          "mt-2.5 min-h-5 px-3 text-sm",
          showError ? "text-destructive-deep" : "text-on-surface-variant"
        )}
      >
        {showError ? (
          "Escribe un dominio público válido, p. ej. ejemplo.gob.mx"
        ) : host && valid ? (
          <>
            Vas a auditar{" "}
            <span className="font-mono font-medium text-foreground">
              {host}
            </span>
          </>
        ) : (
          <>
            Nivel básico:{" "}
            <span className="text-foreground">
              pasivo, anónimo y sin registro
            </span>{" "}
            — listo en &lt;90s.
          </>
        )}
      </p>
    </form>
  );
}
