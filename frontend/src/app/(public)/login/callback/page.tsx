"use client";

import { Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { useSessionActions } from "@/src/application/contexts/session";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";
import { Button } from "@/src/presentation/components/ui/button";

type Phase = "verifying" | "redirecting" | "error";

/**
 * §F10 · Google OAuth callback. Google redirects here (this path must match the
 * backend/console `GOOGLE_REDIRECT_URI`) with `?code=` on success or `?error=`
 * on cancel/deny. We POST the code to the BFF `/api/auth/google-login`, which
 * exchanges it server-side, sets the HttpOnly session cookies, and returns the
 * resolved post-login `redirect` (the pending destination from §F10). On any
 * failure we bounce back to `/login?error=...` so the user can retry.
 */
export default function GoogleCallbackPage() {
  const t = useTranslations("LoginOwliver");
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setSession } = useSessionActions();

  const [phase, setPhase] = useState<Phase>("verifying");
  const ran = useRef(false);

  useEffect(() => {
    // React 18 StrictMode double-invokes effects in dev — guard the one-shot
    // code exchange (a code is single-use).
    if (ran.current) return;
    ran.current = true;

    const code = searchParams.get("code");
    const oauthError = searchParams.get("error");

    if (oauthError || !code) {
      router.replace("/login?error=oauth");
      return;
    }

    (async () => {
      try {
        const res = await fetch("/api/auth/google-login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        });
        const result = await res.json().catch(() => null);

        if (!res.ok || !result || isErrorFeedback(result)) {
          router.replace("/login?error=exchange");
          return;
        }

        const { user, tenant, tenantRole, redirect } = result.data;
        setSession(user, tenant, tenantRole, "");

        setPhase("redirecting");
        router.replace(typeof redirect === "string" ? redirect : "/watchlist");
      } catch {
        setPhase("error");
      }
    })();
    // setSession is a stable zustand action; searchParams/router are stable refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="grid min-h-screen place-items-center bg-background px-4 py-12">
      <div className="flex w-full max-w-sm flex-col items-center gap-8 text-center">
        <BrandLockup href={null} size="lg" owlState="running" />

        {phase === "error" ? (
          <div className="flex flex-col items-center gap-4">
            <div className="space-y-1">
              <h1 className="text-xl font-semibold tracking-tight text-foreground">
                {t("errors.title")}
              </h1>
              <p className="text-sm text-muted-foreground">{t("errors.exchange")}</p>
            </div>
            <Button
              variant="default"
              size="lg"
              onClick={() => router.replace("/login")}
            >
              {t("errors.retry")}
            </Button>
          </div>
        ) : (
          <p
            className="flex items-center gap-2 text-sm text-muted-foreground"
            aria-live="polite"
          >
            <Loader2 className="size-4 animate-spin" />
            {phase === "redirecting" ? t("redirecting") : t("verifying")}
          </p>
        )}
      </div>
    </div>
  );
}
