"use client";

import { useMemo } from "react";
import { useOnboardTenantWizardStore } from "@/src/application/stores/onboard-tenant-wizard-store";
import { COUNTRIES } from "@/src/domain/catalogs/countries";
import { CURRENCIES } from "@/src/domain/catalogs/currencies";
import { TIMEZONES } from "@/src/domain/catalogs/timezones";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { slugify } from "./slug";

const STAR = "⭐";

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

export function StepInfo() {
  return (
    <div className="space-y-5">
      <TenantNameField />
      <TenantLocaleFields />
    </div>
  );
}

function TenantNameField() {
  const name = useOnboardTenantWizardStore((s) => s.name);
  const setName = useOnboardTenantWizardStore((s) => s.setName);

  const slugPreview = slugify(name) || "tenant";

  return (
    <div className="space-y-1.5">
      <Label htmlFor="tenant-name" className="text-xs font-medium">
        Nombre del cliente
      </Label>
      <Input
        id="tenant-name"
        placeholder="Acme Microcréditos"
        value={name}
        onValueChange={(v) => setName(v as string)}
        autoFocus
      />
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
        slug: {slugPreview}
      </p>
    </div>
  );
}

function TenantLocaleFields() {
  const countryCode = useOnboardTenantWizardStore((s) => s.countryCode);
  const currencyCode = useOnboardTenantWizardStore((s) => s.currencyCode);
  const timeZone = useOnboardTenantWizardStore((s) => s.timeZone);
  const setCountryCode = useOnboardTenantWizardStore((s) => s.setCountryCode);
  const setCurrencyCode = useOnboardTenantWizardStore((s) => s.setCurrencyCode);
  const setTimeZone = useOnboardTenantWizardStore((s) => s.setTimeZone);

  const countries = useMemo(() => sortPopularFirst(COUNTRIES), []);
  const currencies = useMemo(() => sortPopularFirst(CURRENCIES), []);
  const timezones = useMemo(() => sortPopularFirst(TIMEZONES), []);

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs font-medium">País</Label>
          <Select
            value={countryCode}
            onValueChange={(v) => v && setCountryCode(v)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Elegir…" />
            </SelectTrigger>
            <SelectContent>
              {countries.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  <span className="mr-2">{c.flag}</span>
                  {c.label}
                  {c.popular ? (
                    <span className="ml-1 text-[10px] opacity-60">{STAR}</span>
                  ) : null}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs font-medium">Moneda</Label>
          <Select
            value={currencyCode}
            onValueChange={(v) => v && setCurrencyCode(v)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Elegir…" />
            </SelectTrigger>
            <SelectContent>
              {currencies.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  <span className="font-mono text-[11px] mr-2">{c.code}</span>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label className="text-xs font-medium">Zona horaria</Label>
        <Select value={timeZone} onValueChange={(v) => v && setTimeZone(v)}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Elegir…" />
          </SelectTrigger>
          <SelectContent>
            {timezones.map((tz) => (
              <SelectItem key={tz.code} value={tz.code}>
                {tz.label}
                <span className="ml-2 font-mono text-[10px] opacity-60">
                  {tz.code}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
