"use client";

import { AlertTriangle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { FcGoogle } from "react-icons/fc";

import { cn } from "@/src/application/lib/utils";
import { Button } from "@/src/presentation/components/ui/button";
import { LocaleSwitcher } from "@/src/presentation/components/locale-switcher";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";

/** Map the `?error=` flag (from the start route / callback) to a copy key. */
function errorKey(raw: string | null): "oauth" | "config" | "exchange" | null {
  if (raw === "config") return "config";
  if (raw === "exchange") return "exchange";
  if (raw) return "oauth";
  return null;
}

/**
 * §F10 · Login Google (`(public)`). Owliver reuses the boilerplate Google OAuth
 * (no magic-link, no password). The button is a same-origin link to the server
 * route `/api/auth/google/start`, which holds the Google client_id/redirect_uri
 * server-side and 302s to Google's consent screen; the `?next=` destination is
 * stashed in an HttpOnly cookie for after login (§F10: "destino pendiente").
 *
 * This page is NOT wrapped by the Owliver public chrome — it lives directly under
 * `(public)/login`, with its own centered card, like the boilerplate auth pages.
 */
export default function LoginPage() {
  const t = useTranslations("LoginOwliver");
  const searchParams = useSearchParams();
  const [connecting, setConnecting] = useState(false);

  // Preserve the intended destination (e.g. the active-scan form that bounced
  // here). Only same-site relative paths are forwarded.
  const rawNext = searchParams.get("next");
  const next = rawNext && rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : null;

  const startHref = next
    ? `/api/auth/google/start?next=${encodeURIComponent(next)}`
    : "/api/auth/google/start";

  const error = errorKey(searchParams.get("error"));

  return (
    <div className="relative grid min-h-screen place-items-center bg-background px-4 py-12">
      <div className="absolute top-4 right-4 z-10">
        <LocaleSwitcher />
      </div>

      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-8 rounded-3xl border border-border bg-card p-8 shadow-sm sm:p-10">
          <BrandLockup href="/" size="lg" owlState="idle" />

          <div className="space-y-2 text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              {t("title")}
            </h1>
            <p className="text-sm text-muted-foreground text-pretty">
              {t("description")}
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="w-full rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive-deep"
            >
              <p className="flex items-center gap-2 font-medium">
                <AlertTriangle className="size-4 shrink-0" />
                {t("errors.title")}
              </p>
              <p className="mt-1 pl-6 text-destructive-deep/90">
                {t(`errors.${error}`)}
              </p>
            </div>
          )}

          <Button
            nativeButton={false}
            render={
              // Base UI Button uses `render` (no asChild) — the canonical
              // link-styled-button pattern in this codebase.
              <Link href={startHref} />
            }
            variant="outline"
            size="lg"
            disabled={connecting}
            onClick={() => setConnecting(true)}
            className={cn(
              "w-full border-outline-variant bg-card font-medium text-foreground",
              "hover:bg-accent/40"
            )}
          >
            <FcGoogle className="size-5" />
            {connecting ? t("connecting") : t("continueWithGoogle")}
          </Button>

          <p className="max-w-xs text-center text-xs text-muted-foreground/80 text-pretty">
            {t("legal")}
          </p>
        </div>

        <div className="mt-6 text-center">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-lg text-sm text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ArrowLeft className="size-4" />
            {t("back")}
          </Link>
        </div>
      </div>
    </div>
  );
}
