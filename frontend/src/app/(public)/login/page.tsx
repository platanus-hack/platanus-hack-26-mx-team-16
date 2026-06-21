"use client";

import { AlertTriangle, ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";
import { FcGoogle } from "react-icons/fc";

import { useSessionActions } from "@/src/application/contexts/session";
import { cn } from "@/src/application/lib/utils";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import { LocaleSwitcher } from "@/src/presentation/components/locale-switcher";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";

/** Default post-login destination — mirrors the Google `google-login` route. */
const DEFAULT_DEST = "/watcher";

/** Map the `?error=` flag (from the start route / callback) to a copy key. */
function errorKey(raw: string | null): "oauth" | "config" | "exchange" | null {
  if (raw === "config") return "config";
  if (raw === "exchange") return "exchange";
  if (raw) return "oauth";
  return null;
}

/**
 * §F10 · Login (`(public)`). Owliver supports two paths into a session:
 * email + password (the boilerplate `/api/auth/login` BFF, which sets the
 * HttpOnly session cookies) and Google OAuth. The Google button is a same-origin
 * link to `/api/auth/google/start`, which holds the client_id/redirect_uri
 * server-side and 302s to Google's consent screen; the `?next=` destination is
 * stashed in an HttpOnly cookie for after login (§F10: "destino pendiente").
 *
 * This page is NOT wrapped by the Owliver public chrome — it lives directly under
 * `(public)/login`, with its own centered card, like the boilerplate auth pages.
 */
export default function LoginPage() {
  const t = useTranslations("LoginOwliver");
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setSession } = useSessionActions();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [formError, setFormError] = useState<"credentials" | "fields" | "generic" | null>(null);

  // Preserve the intended destination (e.g. the active-scan form that bounced
  // here). Only same-site relative paths are forwarded.
  const rawNext = searchParams.get("next");
  const next = rawNext && rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : null;

  const startHref = next
    ? `/api/auth/google/start?next=${encodeURIComponent(next)}`
    : "/api/auth/google/start";

  const oauthError = errorKey(searchParams.get("error"));

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    if (!email.trim() || !password) {
      setFormError("fields");
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const result = await res.json().catch(() => null);

      if (!res.ok || !result || isErrorFeedback(result)) {
        setFormError(res.status === 401 || res.status === 400 ? "credentials" : "generic");
        setSubmitting(false);
        return;
      }

      const { user, tenant, tenantRole } = result.data;
      setSession(user, tenant, tenantRole, "");
      router.replace(next ?? DEFAULT_DEST);
    } catch {
      setFormError("generic");
      setSubmitting(false);
    }
  }

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

          {(oauthError || formError) && (
            <div
              role="alert"
              className="w-full rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive-deep"
            >
              <p className="flex items-center gap-2 font-medium">
                <AlertTriangle className="size-4 shrink-0" />
                {t("errors.title")}
              </p>
              <p className="mt-1 pl-6 text-destructive-deep/90">
                {t(`errors.${formError ?? oauthError}`)}
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="w-full space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="email">{t("emailLabel")}</Label>
              <Input
                id="email"
                type="email"
                name="email"
                autoComplete="email"
                className="h-11"
                placeholder={t("emailPlaceholder")}
                value={email}
                onValueChange={(value) => setEmail(value)}
                disabled={submitting}
                aria-invalid={formError === "credentials" || formError === "fields"}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">{t("passwordLabel")}</Label>
                <Link
                  href="/reset-password"
                  className="rounded text-xs font-medium text-primary outline-none transition-colors hover:text-primary/80 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {t("forgotPassword")}
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                name="password"
                autoComplete="current-password"
                className="h-11"
                placeholder={t("passwordPlaceholder")}
                value={password}
                onValueChange={(value) => setPassword(value)}
                disabled={submitting}
                aria-invalid={formError === "credentials" || formError === "fields"}
              />
            </div>

            <Button
              type="submit"
              variant="default"
              size="lg"
              disabled={submitting}
              className="w-full font-medium"
            >
              {submitting && <Loader2 className="size-4 animate-spin" />}
              {submitting ? t("signingIn") : t("signIn")}
            </Button>
          </form>

          <div className="flex w-full items-center gap-3">
            <span className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">{t("orContinueWith")}</span>
            <span className="h-px flex-1 bg-border" />
          </div>

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
