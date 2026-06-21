"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { useSessionActions } from "@/src/application/contexts/session";
import {
  type CreateTenantFormData,
  createTenantFormSchema,
} from "@/src/application/schemas/tenant.schema";
import { COUNTRIES } from "@/src/domain/catalogs/countries";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";

function sortPopularFirst<T extends { popular?: boolean; label: string }>(
  list: T[]
): T[] {
  return [...list].sort((a, b) => {
    const ap = a.popular ? 0 : 1;
    const bp = b.popular ? 0 : 1;
    if (ap !== bp) return ap - bp;
    return a.label.localeCompare(b.label);
  });
}

export function UnassignedView() {
  const t = useTranslations("Unassigned");
  const router = useRouter();
  const { clearSession } = useSessionActions();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const countries = useMemo(() => sortPopularFirst(COUNTRIES), []);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CreateTenantFormData>({
    resolver: zodResolver(createTenantFormSchema),
    defaultValues: { name: "", countryCode: "MX" },
  });

  const onSubmit = async (data: CreateTenantFormData) => {
    setSubmitError(null);
    try {
      const res = await fetch("/api/tenants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: data.name,
          countryCode: data.countryCode,
        }),
      });
      const payload = await res.json().catch(() => null);

      if (!res.ok || (payload && isErrorFeedback(payload))) {
        const message =
          payload && isErrorFeedback(payload) && payload.errors[0]?.message
            ? payload.errors[0].message
            : t("error");
        setSubmitError(message);
        return;
      }

      // Tenant created — the user is now its owner. Land on home; refresh()
      // re-runs the server layout so the new (tenant-scoped) session is picked up.
      router.replace("/");
      router.refresh();
    } catch {
      setSubmitError(t("error"));
    }
  };

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    clearSession();
    router.push("/login");
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Building2 className="h-5 w-5" />
        </div>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <FieldGroup>
            <Field>
              <FieldContent>
                <FieldTitle>{t("nameLabel")}</FieldTitle>
                <Input
                  placeholder={t("namePlaceholder")}
                  autoFocus
                  disabled={isSubmitting}
                  {...register("name")}
                />
                <FieldError errors={errors.name ? [errors.name] : []} />
              </FieldContent>
            </Field>

            <Field>
              <FieldContent>
                <FieldTitle>{t("countryLabel")}</FieldTitle>
                <Controller
                  control={control}
                  name="countryCode"
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={(v) => v && field.onChange(v)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder={t("countryPlaceholder")} />
                      </SelectTrigger>
                      <SelectContent>
                        {countries.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            <span className="mr-2">{c.flag}</span>
                            {c.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                <FieldError
                  errors={errors.countryCode ? [errors.countryCode] : []}
                />
              </FieldContent>
            </Field>

            {submitError && (
              <div className="text-destructive text-sm" role="alert">
                {submitError}
              </div>
            )}

            <ActionButton
              type="submit"
              className="w-full"
              loading={isSubmitting}
              icon={<Building2 className="h-4 w-4" />}
            >
              {isSubmitting ? t("submitting") : t("submit")}
            </ActionButton>
          </FieldGroup>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col gap-3">
        <p className="px-2 text-center text-xs text-muted-foreground">
          {t("footer")}
        </p>
        <button
          type="button"
          onClick={handleLogout}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
        >
          <LogOut className="h-3.5 w-3.5" />
          {t("logout")}
        </button>
      </CardFooter>
    </Card>
  );
}
