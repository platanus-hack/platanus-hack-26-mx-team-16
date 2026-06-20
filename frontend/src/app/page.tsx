"use client";

import { Lock, Mail } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { FcGoogle } from "react-icons/fc";

import { useSessionActions } from "@/src/application/contexts/session";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { AuthContainer } from "@/src/presentation/components/auth-container";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Field,
  FieldContent,
  FieldError,
} from "@/src/presentation/components/ui/field";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

export default function Page() {
  const t = useTranslations("Login");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>(
    {}
  );
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState("");
  const { setSession } = useSessionActions();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: { email?: string; password?: string } = {};

    if (!email) {
      newErrors.email = t("errors.emailRequired");
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = t("errors.emailInvalid");
    }

    if (!password) {
      newErrors.password = t("errors.passwordRequired");
    } else if (password.length < 6) {
      newErrors.password = t("errors.passwordTooShort");
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      setIsLoading(true);
      setServerError("");

      try {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email, password }),
        });

        const result = await response.json();

        if (!response.ok) {
          if (isErrorFeedback(result)) {
            setServerError(
              result.errors[0]?.message || t("errors.loginFailed")
            );
          } else {
            setServerError(t("errors.loginFailed"));
          }
          return;
        }

        const { user, tenant, tenantRole } = result.data;
        setSession(user, tenant, tenantRole, "");

        router.push(tenant ? "/dashboard" : "/unassigned");
      } catch (err) {
        console.error("Error en login:", err);
        setServerError(t("errors.connectionError"));
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <AuthContainer
      icon={Lock}
      title={t("title")}
      description={t("description")}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {serverError && (
          <div
            className="text-destructive rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm"
            role="alert"
          >
            {serverError}
          </div>
        )}

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
                disabled={isLoading}
              />
            </div>
            {errors.email && <FieldError>{errors.email}</FieldError>}
          </FieldContent>
        </Field>

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
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={!!errors.password}
                className="pl-10"
                disabled={isLoading}
              />
            </div>
            {errors.password && <FieldError>{errors.password}</FieldError>}
          </FieldContent>
        </Field>

        <div>
          <Link
            href="/reset-password"
            className="text-sm text-foreground hover:underline mb-2 block"
          >
            {t("forgotPassword")}
          </Link>
          <Button
            type="submit"
            className="w-full bg-foreground text-background hover:bg-foreground/90 font-semibold"
            disabled={isLoading}
          >
            {isLoading ? t("submitting") : t("submit")}
          </Button>
        </div>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-background px-3 text-foreground">
            {t("orContinueWith")}
          </span>
        </div>
      </div>

      <Button
        variant="outline"
        className="w-full font-medium"
        onClick={() => console.log("Login con Google")}
        disabled={isLoading}
      >
        <FcGoogle className="mr-2 h-5 w-5" />
        {t("continueWithGoogle")}
      </Button>

      <div>
        <p className="text-center text-sm text-muted-foreground">
          {t("noAccount")}{" "}
          <Link
            href="/register"
            className="font-semibold text-foreground hover:underline"
          >
            {t("createAccount")}
          </Link>
        </p>
      </div>
    </AuthContainer>
  );
}
