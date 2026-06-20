"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";

import {
  type LoginFormData,
  loginFormSchema,
} from "@/src/application/schemas/auth.schema";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import {
  Field,
  FieldContent,
  FieldError,
  FieldGroup,
  FieldTitle,
} from "@/src/presentation/components/ui/field";
import { Input } from "@/src/presentation/components/ui/input";

interface AuthFormProps {
  onSubmit: (data: LoginFormData) => Promise<void>;
  isLoading?: boolean;
  error?: string;
}

export function AuthForm({
  onSubmit,
  isLoading = false,
  error,
}: AuthFormProps) {
  const t = useTranslations("Login");
  const [_showPassword, _setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const handleFormSubmit = async (data: LoginFormData) => {
    await onSubmit(data);
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(handleFormSubmit)}>
          <FieldGroup>
            <Field>
              <FieldContent>
                <FieldTitle>{t("emailLabel")}</FieldTitle>
                <Input
                  type="email"
                  placeholder={t("emailPlaceholder")}
                  {...register("email")}
                  disabled={isLoading}
                />
                <FieldError errors={errors.email ? [errors.email] : []} />
              </FieldContent>
            </Field>

            <Field>
              <FieldContent>
                <FieldTitle>{t("passwordLabel")}</FieldTitle>
                <Input
                  type={_showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  {...register("password")}
                  disabled={isLoading}
                />
                <FieldError
                  errors={errors.password ? [errors.password] : []}
                />
              </FieldContent>
            </Field>

            {error && (
              <div className="text-destructive text-sm" role="alert">
                {error}
              </div>
            )}

            <ActionButton type="submit" className="w-full" loading={isLoading}>
              {isLoading ? t("submitting") : t("submit")}
            </ActionButton>
          </FieldGroup>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col gap-2">
        <button
          type="button"
          className="text-muted-foreground hover:text-primary text-sm underline underline-offset-4"
          onClick={() => {
            // TODO: Implementar recuperación de contraseña
          }}
        >
          {t("forgotPassword")}
        </button>
      </CardFooter>
    </Card>
  );
}
