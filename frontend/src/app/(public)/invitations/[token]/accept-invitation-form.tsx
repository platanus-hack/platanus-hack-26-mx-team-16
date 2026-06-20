"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, useTransition } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

interface Props {
  token: string;
  requiresPassword: boolean;
}

export function AcceptInvitationForm({ token, requiresPassword }: Props) {
  const t = useTranslations("Invitations");
  const router = useRouter();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const passwordsMatch = password === confirm;
  const passwordOk =
    !requiresPassword || (password.length >= 8 && passwordsMatch);
  const canSubmit = passwordOk && firstName.trim().length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    startTransition(async () => {
      try {
        const body: Record<string, unknown> = {
          firstName: firstName.trim(),
          lastName: lastName.trim() || null,
        };
        if (requiresPassword) body.password = password;

        const res = await fetch(
          `/api/auth/invitations/${encodeURIComponent(token)}/accept`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            credentials: "include",
          }
        );
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          setError(data?.errors?.[0]?.message ?? t("errors.acceptFailed"));
          return;
        }
        router.push("/dashboard");
      } catch {
        setError(t("errors.connectionError"));
      }
    });
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="firstName" className="text-xs font-medium">
            {t("firstName")}
          </Label>
          <Input
            id="firstName"
            value={firstName}
            onValueChange={setFirstName}
            autoFocus
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="lastName" className="text-xs font-medium">
            {t("lastName")}
          </Label>
          <Input id="lastName" value={lastName} onValueChange={setLastName} />
        </div>
      </div>

      {requiresPassword ? (
        <>
          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-xs font-medium">
              {t("passwordLabel")}
            </Label>
            <Input
              id="password"
              type="password"
              value={password}
              onValueChange={setPassword}
              minLength={8}
              required
            />
            <p className="text-[11px] text-muted-foreground">{t("minChars")}</p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirm" className="text-xs font-medium">
              {t("confirmPasswordLabel")}
            </Label>
            <Input
              id="confirm"
              type="password"
              value={confirm}
              onValueChange={setConfirm}
              minLength={8}
              required
              aria-invalid={confirm.length > 0 && !passwordsMatch}
            />
            {confirm.length > 0 && !passwordsMatch ? (
              <p className="text-[11px] text-destructive">
                {t("passwordsDontMatch")}
              </p>
            ) : null}
          </div>
        </>
      ) : (
        <p className="rounded-md border border-border bg-muted/40 p-3 text-[11px] text-muted-foreground">
          {t("existingAccountNote")}
        </p>
      )}

      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      <Button
        type="submit"
        className="w-full gap-2"
        disabled={!canSubmit || isPending}
      >
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        {isPending
          ? t("accepting")
          : requiresPassword
            ? t("acceptLabel")
            : t("joinTenant")}
      </Button>
    </form>
  );
}
