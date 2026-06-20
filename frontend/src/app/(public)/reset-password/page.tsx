"use client";

import { KeyRound, Mail } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { AuthContainer } from "@/src/presentation/components/auth-container";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Field,
  FieldContent,
  FieldError,
} from "@/src/presentation/components/ui/field";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

export default function ResetPasswordPage() {
  const t = useTranslations("ResetPassword");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<{ email?: string }>({});
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: { email?: string } = {};
    if (!email) {
      newErrors.email = t("errors.emailRequired");
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = t("errors.emailInvalid");
    }
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) return;

    setIsLoading(true);
    setServerError("");
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (!res.ok) {
        setServerError(t("errors.requestFailed"));
        return;
      }
      setSubmitted(true);
    } catch {
      setServerError(t("errors.connectionError"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContainer
      icon={KeyRound}
      title={t("title")}
      description={t("description")}
    >
      {!submitted ? (
        <>
          <form onSubmit={handleSubmit} className="space-y-5">
            <Field data-invalid={!!errors.email}>
              <Label htmlFor="email" className="text-sm font-semibold">
                {t("emailLabel")}
              </Label>
              <FieldContent>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder={t("emailPlaceholder")}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    aria-invalid={!!errors.email}
                    className="pl-10"
                  />
                </div>
                {errors.email && <FieldError>{errors.email}</FieldError>}
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
              {t("rememberedPassword")}{" "}
              <Link
                href="/"
                className="font-semibold text-foreground hover:underline"
              >
                {t("signIn")}
              </Link>
            </p>
          </div>
        </>
      ) : (
        <div className="space-y-5">
          <div className="rounded-lg bg-primary/10 p-4 text-center">
            <p className="text-sm text-foreground">
              {t.rich("successMessage", {
                email,
                strong: (chunks) => <strong>{chunks}</strong>,
              })}
            </p>
          </div>

          <Button
            onClick={() => {
              setSubmitted(false);
              setEmail("");
            }}
            variant="outline"
            className="w-full font-medium"
          >
            {t("tryAgain")}
          </Button>

          <div>
            <p className="text-center text-sm text-muted-foreground">
              <Link
                href="/"
                className="font-semibold text-foreground hover:underline"
              >
                {t("backToLogin")}
              </Link>
            </p>
          </div>
        </div>
      )}
    </AuthContainer>
  );
}
