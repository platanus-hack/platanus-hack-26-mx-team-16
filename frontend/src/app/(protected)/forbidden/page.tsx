"use client";

import { ShieldX } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { useSessionActions } from "@/src/application/contexts/session";
import { buttonVariants } from "@/src/presentation/components/ui/button";

export default function ForbiddenPage() {
  const t = useTranslations("Forbidden");
  const router = useRouter();
  const { clearSession } = useSessionActions();

  const handleSignOut = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    clearSession();
    router.replace("/");
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-md flex flex-col items-center gap-6">
        <div className="flex items-center justify-center w-20 h-20 rounded-full bg-destructive/10">
          <ShieldX className="w-10 h-10 text-destructive" />
        </div>

        <div className="text-center space-y-1">
          <p className="text-sm font-semibold text-destructive uppercase tracking-wider">
            {t("errorTag")}
          </p>
          <h1 className="text-2xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground text-sm mt-2">
            {t("description")}
          </p>
        </div>

        <div className="w-full rounded-lg border bg-muted/40 px-5 py-4 text-sm text-muted-foreground space-y-1">
          <p className="font-medium text-foreground">{t("currentRole")}</p>
        </div>

        <div className="w-full rounded-lg border px-5 py-4 space-y-3">
          <p className="text-sm font-medium">{t("nextStepsTitle")}</p>
          <ul className="text-sm text-muted-foreground space-y-1.5 list-disc list-inside">
            <li>{t("step1")}</li>
            <li>{t("step2")}</li>
            <li>{t("step3")}</li>
          </ul>
        </div>

        <div className="flex gap-3 w-full">
          <Link
            href="/dashboard"
            className={buttonVariants({ className: "flex-1" })}
          >
            {t("goHome")}
          </Link>
          <button
            onClick={handleSignOut}
            className={buttonVariants({
              variant: "outline",
              className: "flex-1",
            })}
          >
            {t("logout")}
          </button>
        </div>

        <p className="text-xs text-muted-foreground text-center">
          {t("footer")}
        </p>
      </div>
    </div>
  );
}
