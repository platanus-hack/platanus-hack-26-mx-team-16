"use client";

import { CheckCircle, KeyRound, Lock } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { use, useState } from "react";

import { AuthContainer } from "@/src/presentation/components/auth-container";
import {
  Button,
  buttonVariants,
} from "@/src/presentation/components/ui/button";
import {
  Field,
  FieldContent,
  FieldError,
} from "@/src/presentation/components/ui/field";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

export default function ResetPasswordTokenPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const t = useTranslations("ResetPasswordToken");
  const { token } = use(params);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<{
    password?: string;
    confirm?: string;
  }>({});
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const next: typeof errors = {};
    if (password.length < 8) next.password = t("errors.passwordTooShort");
    if (password !== confirm) next.confirm = t("errors.passwordsDontMatch");
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setIsLoading(true);
    setServerError("");
    try {
      const res = await fetch("/api/auth/reset-password/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as {
          errors?: { code?: string; message?: string }[];
        };
        const code = body?.errors?.[0]?.code ?? "";
        if (code === "common.InvalidOrExpiredToken") {
          setServerError(t("invalidLink"));
        } else {
          setServerError(
            body?.errors?.[0]?.message ?? t("errors.requestFailed")
          );
        }
        return;
      }
      setSuccess(true);
    } catch {
      setServerError(t("errors.connectionError"));
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <AuthContainer
        icon={CheckCircle}
        title={t("successTitle")}
        description={t("successDescription")}
      >
        <Link
          href="/"
          className={buttonVariants({ className: "w-full font-semibold" })}
        >
          {t("signIn")}
        </Link>
      </AuthContainer>
    );
  }

  return (
    <AuthContainer
      icon={KeyRound}
      title={t("title")}
      description={t("description")}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <Field data-invalid={!!errors.password}>
          <Label htmlFor="password" className="text-sm font-semibold">
            {t("passwordLabel")}
          </Label>
          <FieldContent>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={!!errors.password}
                minLength={8}
                className="pl-10"
                autoFocus
              />
            </div>
            {errors.password && <FieldError>{errors.password}</FieldError>}
          </FieldContent>
        </Field>

        <Field data-invalid={!!errors.confirm}>
          <Label htmlFor="confirm" className="text-sm font-semibold">
            {t("confirmPasswordLabel")}
          </Label>
          <FieldContent>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                aria-invalid={!!errors.confirm}
                minLength={8}
                className="pl-10"
              />
            </div>
            {errors.confirm && <FieldError>{errors.confirm}</FieldError>}
          </FieldContent>
        </Field>

        {serverError ? (
          <p className="text-sm text-destructive" role="alert">
            {serverError}
          </p>
        ) : null}

        <Button
          type="submit"
          disabled={isLoading}
          className="w-full bg-foreground text-background hover:bg-foreground/90 font-semibold"
        >
          {isLoading ? t("submitting") : t("submit")}
        </Button>
      </form>

      <div>
        <p className="text-center text-sm text-muted-foreground">
          <Link
            href="/reset-password"
            className="font-semibold text-foreground hover:underline"
          >
            {t("requestNew")}
          </Link>
        </p>
      </div>
    </AuthContainer>
  );
}
