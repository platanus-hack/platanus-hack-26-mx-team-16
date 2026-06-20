"use client";

import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

import { setLocale } from "@/src/app/actions/locale";
import { cn } from "@/src/application/lib/utils";
import { type Locale, localeLabels, locales } from "@/src/i18n/config";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/src/presentation/components/ui/select";

export function LocaleSwitcher({ className }: { className?: string }) {
  const t = useTranslations("LocaleSwitcher");
  const currentLocale = useLocale() as Locale;
  const [isPending, startTransition] = useTransition();

  const handleChange = (next: string | null) => {
    if (!next || next === currentLocale) return;
    startTransition(() => {
      void setLocale(next);
    });
  };

  return (
    <Select
      value={currentLocale}
      onValueChange={handleChange}
      disabled={isPending}
    >
      <SelectTrigger
        size="sm"
        aria-label={t("ariaLabel")}
        className={cn(
          "h-8 w-auto min-w-0 gap-1 px-2 text-xs font-medium uppercase tracking-wide",
          "border-0 bg-transparent shadow-none text-muted-foreground",
          "hover:bg-accent hover:text-foreground",
          "dark:bg-transparent dark:hover:bg-accent",
          "focus-visible:ring-0 focus-visible:border-0",
          className
        )}
      >
        <span>{currentLocale.toUpperCase()}</span>
      </SelectTrigger>
      <SelectContent align="end">
        {locales.map((loc) => (
          <SelectItem key={loc} value={loc}>
            <span className="font-mono text-xs font-semibold uppercase tracking-wide mr-2">
              {loc.toUpperCase()}
            </span>
            <span className="text-sm text-muted-foreground">
              {localeLabels[loc]}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
