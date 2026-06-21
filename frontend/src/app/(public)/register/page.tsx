"use client";

import { Lock, Mail, User, UserPlus } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { FcGoogle } from "react-icons/fc";
import { AuthContainer } from "@/src/presentation/components/auth-container";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Field,
  FieldContent,
  FieldError,
} from "@/src/presentation/components/ui/field";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

export default function RegisterPage() {
  const t = useTranslations("Register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<{
    name?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: {
      name?: string;
      email?: string;
      password?: string;
      confirmPassword?: string;
    } = {};

    if (!name) {
      newErrors.name = t("errors.nameRequired");
    } else if (name.length < 2) {
      newErrors.name = t("errors.nameTooShort");
    }

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

    if (!confirmPassword) {
      newErrors.confirmPassword = t("errors.confirmPasswordRequired");
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = t("errors.passwordsDontMatch");
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      console.log("Creando cuenta con:", { name, email, password });
    }
  };

  return (
    <AuthContainer
      icon={UserPlus}
      title={t("title")}
      description={t("description")}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <Field data-invalid={!!errors.name}>
          <Label htmlFor="name" className="text-sm font-semibold">
            {t("nameLabel")}
          </Label>
          <FieldContent>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="name"
                type="text"
                placeholder={t("namePlaceholder")}
                value={name}
                onValueChange={setName}
                aria-invalid={!!errors.name}
                className="pl-10"
              />
            </div>
            {errors.name && <FieldError>{errors.name}</FieldError>}
          </FieldContent>
        </Field>

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
                onValueChange={setEmail}
                aria-invalid={!!errors.email}
                className="pl-10"
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
                onValueChange={setPassword}
                aria-invalid={!!errors.password}
                className="pl-10"
              />
            </div>
            {errors.password && <FieldError>{errors.password}</FieldError>}
          </FieldContent>
        </Field>

        <Field data-invalid={!!errors.confirmPassword}>
          <Label htmlFor="confirmPassword" className="text-sm font-semibold">
            {t("confirmPasswordLabel")}
          </Label>
          <FieldContent>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onValueChange={setConfirmPassword}
                aria-invalid={!!errors.confirmPassword}
                className="pl-10"
              />
            </div>
            {errors.confirmPassword && (
              <FieldError>{errors.confirmPassword}</FieldError>
            )}
          </FieldContent>
        </Field>

        <Button
          type="submit"
          className="w-full bg-foreground text-background hover:bg-foreground/90 font-semibold"
        >
          {t("submit")}
        </Button>
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
        onClick={() => console.log("Registro con Google")}
      >
        <FcGoogle className="mr-2 h-5 w-5" />
        {t("continueWithGoogle")}
      </Button>

      <div>
        <p className="text-center text-sm text-muted-foreground">
          {t("haveAccount")}{" "}
          <Link
            href="/"
            className="font-semibold text-foreground hover:underline"
          >
            {t("signIn")}
          </Link>
        </p>
      </div>
    </AuthContainer>
  );
}
