"use client";

import { AlertCircle, LogOut, Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { useSessionActions } from "@/src/application/contexts/session";
import {
  Alert,
  AlertDescription,
} from "@/src/presentation/components/ui/alert";
import { Button } from "@/src/presentation/components/ui/button";

export function UnassignedView() {
  const t = useTranslations("Unassigned");
  const router = useRouter();
  const { clearSession } = useSessionActions();

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    clearSession();
    router.push("/");
  };

  return (
    <div className="mx-auto flex w-full max-w-md flex-col space-y-6">
      <div className="flex flex-col items-center space-y-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-warning/10">
          <AlertCircle className="h-8 w-8 text-warning" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
        <p className="px-4 text-sm leading-5 text-muted-foreground">
          {t("description")}
        </p>
      </div>

      <Alert className="border-warning/30 bg-warning/5">
        <AlertCircle className="h-4 w-4 text-warning" />
        <AlertDescription>{t("alert")}</AlertDescription>
      </Alert>

      <div className="rounded-lg border border-border bg-muted/50 p-4">
        <h3 className="mb-2 font-medium">{t("nextStepsTitle")}</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <span className="select-none text-muted-foreground/60">•</span>
            {t("step1")}
          </li>
          <li className="flex items-start gap-2">
            <span className="select-none text-muted-foreground/60">•</span>
            {t("step2")}
          </li>
          <li className="flex items-start gap-2">
            <span className="select-none text-muted-foreground/60">•</span>
            {t("step3")}
          </li>
        </ul>
      </div>

      <div className="flex gap-2">
        <Button
          className="flex-1 gap-2"
          nativeButton={false}
          render={<a href="mailto:support@llamitai.com" />}
        >
          <Mail className="h-4 w-4" />
          {t("support")}
        </Button>
        <Button
          variant="outline"
          onClick={handleLogout}
          className="flex-1 gap-2"
        >
          <LogOut className="h-4 w-4" />
          {t("logout")}
        </Button>
      </div>

      <p className="px-4 text-center text-xs text-muted-foreground">
        {t("footer")}
      </p>
    </div>
  );
}
