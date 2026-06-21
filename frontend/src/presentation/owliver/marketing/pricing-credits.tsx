/**
 * PricingCredits — credits-based pricing for Owliver. One audit spends credits
 * by depth (básico 1 · intermedio 4 · avanzado 12); plans grant a monthly pool.
 *
 * Interactive: a Mensual/Anual billing toggle and a live "estimator" where the
 * visitor dials how many scans they run and sees the credits + suggested plan
 * update in real time. Stays in the M3 product language — violet for the active
 * path and primary action, the A–F ramp untouched (it is data, not pricing).
 */
"use client";

import { ArrowRight, Building2, Check, Sparkles, Zap } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { cn } from "@/src/application/lib/utils";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";

const CREDIT_COST = [
  { level: "Básico", credits: 1, hint: "pasivo" },
  { level: "Intermedio", credits: 4, hint: "activo" },
  { level: "Avanzado", credits: 12, hint: "explotación" },
] as const;

type Tier = {
  name: string;
  icon: typeof Zap;
  priceMonthly: number | null; // null → "Personalizado"
  priceAnnual: number | null;
  credits: string;
  blurb: string;
  features: string[];
  cta: { label: string; href: string };
  featured?: boolean;
};

const TIERS: Tier[] = [
  {
    name: "Explorador",
    icon: Sparkles,
    priceMonthly: 0,
    priceAnnual: 0,
    credits: "10 créditos / mes",
    blurb: "Para revisar un sitio y subirte al ranking público.",
    features: [
      "Solo nivel Básico (pasivo)",
      "Ranking público .gob.mx",
      "1 sitio en watchlist",
      "Reporte A–F compartible",
    ],
    cta: { label: "Empieza gratis", href: "/scan" },
  },
  {
    name: "Pro",
    icon: Zap,
    priceMonthly: 299,
    priceAnnual: 239,
    credits: "150 créditos / mes",
    blurb: "Para equipos que auditan y monitorean en serio.",
    features: [
      "Todos los niveles (con autorización)",
      "Watchlist ilimitada + re-escaneos",
      "Alertas por email y Slack",
      "Reportes PDF e histórico de grados",
    ],
    cta: { label: "Prueba Pro", href: "/scan" },
    featured: true,
  },
  {
    name: "Equipo",
    icon: Building2,
    priceMonthly: null,
    priceAnnual: null,
    credits: "Bolsas de crédito a escala",
    blurb: "Para gobierno y organizaciones con muchos dominios.",
    features: [
      "Créditos a volumen y por asiento",
      "Roles, SSO y auditoría de acceso",
      "API, webhooks e integraciones",
      "Soporte y onboarding dedicados",
    ],
    cta: { label: "Habla con nosotros", href: "mailto:contact@llamitai.com" },
  },
];

function formatPrice(value: number) {
  return value === 0 ? "$0" : `$${value.toLocaleString("es-MX")}`;
}

export function PricingCredits() {
  const [annual, setAnnual] = React.useState(true);

  // Estimator state — scans/month at each depth.
  const [basic, setBasic] = React.useState(8);
  const [mid, setMid] = React.useState(2);
  const [adv, setAdv] = React.useState(0);
  const total = basic * 1 + mid * 4 + adv * 12;
  const suggested =
    total <= 10 && mid === 0 && adv === 0
      ? "Explorador"
      : total <= 150
        ? "Pro"
        : "Equipo";

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-9 px-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <span className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-secondary">
          Precios
        </span>
        <h2 className="text-balance text-4xl font-bold tracking-tight text-foreground">
          Pagas por lo que auditas
        </h2>
        <p className="max-w-xl text-pretty text-[15px] leading-relaxed text-on-surface-variant">
          Sin licencias por asiento ni sorpresas: compras créditos y cada
          escaneo cuesta según su profundidad.
        </p>

        {/* Credit cost legend */}
        <div className="mt-1 flex flex-wrap items-center justify-center gap-2">
          {CREDIT_COST.map((c) => (
            <span
              key={c.level}
              className="inline-flex items-center gap-2 rounded-full bg-surface-container px-3 py-1.5 text-sm text-on-surface-variant"
            >
              <span className="font-medium text-foreground">{c.level}</span>
              <span className="font-mono text-xs">
                {c.credits} {c.credits === 1 ? "crédito" : "créditos"}
              </span>
            </span>
          ))}
        </div>

        {/* Billing toggle */}
        <div
          role="group"
          aria-label="Periodo de facturación"
          className="mt-2 inline-flex items-center gap-1 rounded-full bg-surface-container p-1"
        >
          {[
            { key: "monthly", label: "Mensual", on: !annual },
            { key: "annual", label: "Anual −20%", on: annual },
          ].map((opt) => (
            <button
              key={opt.key}
              type="button"
              aria-pressed={opt.on}
              onClick={() => setAnnual(opt.key === "annual")}
              className={cn(
                "rounded-full px-4 py-1.5 text-sm font-medium transition-colors duration-200",
                opt.on
                  ? "bg-primary-action text-primary-action-foreground shadow-xs"
                  : "text-on-surface-variant hover:text-foreground"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tier cards */}
      <div className="grid items-start gap-5 lg:grid-cols-3">
        {TIERS.map((tier) => {
          const Icon = tier.icon;
          const price = annual ? tier.priceAnnual : tier.priceMonthly;
          const isFree = tier.priceMonthly === 0;
          return (
            <div
              key={tier.name}
              className={cn(
                "flex h-full flex-col gap-5 rounded-3xl p-7",
                tier.featured
                  ? "bg-card shadow-[0_10px_36px_rgba(40,30,8,0.14)] ring-2 ring-primary"
                  : "border border-outline-variant bg-card"
              )}
            >
              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    "flex size-10 items-center justify-center rounded-2xl",
                    tier.featured
                      ? "bg-primary-action text-primary-action-foreground"
                      : "bg-primary-container text-on-primary-container"
                  )}
                >
                  <Icon className="size-5" />
                </span>
                {tier.featured && (
                  <span className="rounded-full bg-primary-container px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wide text-on-primary-container">
                    Recomendado
                  </span>
                )}
              </div>

              <div className="flex flex-col gap-1">
                <h3 className="text-xl font-bold text-foreground">
                  {tier.name}
                </h3>
                <div className="flex items-end gap-1.5">
                  {price === null ? (
                    <span className="text-3xl font-bold tracking-tight text-foreground">
                      A la medida
                    </span>
                  ) : (
                    <>
                      <span className="font-mono text-4xl font-bold tracking-tight text-foreground tabular-nums">
                        {formatPrice(price)}
                      </span>
                      {!isFree && (
                        <span className="pb-1 text-sm text-on-surface-variant">
                          MXN / mes
                        </span>
                      )}
                    </>
                  )}
                </div>
                <span className="text-sm font-medium text-primary">
                  {tier.credits}
                </span>
              </div>

              <p className="text-[15px] leading-relaxed text-on-surface-variant">
                {tier.blurb}
              </p>

              <ul className="flex flex-1 flex-col gap-2.5">
                {tier.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2.5 text-[15px] text-foreground"
                  >
                    <Check className="mt-0.5 size-4 shrink-0 text-secondary" />
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                href={tier.cta.href}
                className={cn(
                  buttonVariants({
                    variant: tier.featured ? "default" : "outline",
                    size: "lg",
                  }),
                  "w-full"
                )}
              >
                {tier.cta.label}
                <ArrowRight className="size-4" />
              </Link>
            </div>
          );
        })}
      </div>

      {/* Interactive estimator */}
      <div className="grid gap-6 rounded-3xl bg-surface-container-low p-7 md:grid-cols-[1fr_auto] md:items-center md:gap-10 md:p-9">
        <div className="flex flex-col gap-5">
          <div>
            <h3 className="text-lg font-bold text-foreground">
              Estima tus créditos
            </h3>
            <p className="text-sm text-on-surface-variant">
              Ajusta cuántos escaneos corres al mes.
            </p>
          </div>
          <EstimatorSlider
            label="Básicos"
            hint="1 crédito c/u"
            value={basic}
            max={60}
            onChange={setBasic}
          />
          <EstimatorSlider
            label="Intermedios"
            hint="4 créditos c/u"
            value={mid}
            max={30}
            onChange={setMid}
          />
          <EstimatorSlider
            label="Avanzados"
            hint="12 créditos c/u"
            value={adv}
            max={15}
            onChange={setAdv}
          />
        </div>

        <div className="flex flex-col items-center justify-center gap-1 rounded-2xl bg-card px-8 py-7 text-center shadow-xs md:min-w-56">
          <span className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
            Créditos / mes
          </span>
          <span className="font-mono text-5xl font-bold tabular-nums text-foreground">
            {total}
          </span>
          <span className="mt-2 text-sm text-on-surface-variant">
            Plan sugerido
          </span>
          <span className="text-lg font-bold text-primary">{suggested}</span>
        </div>
      </div>
    </div>
  );
}

function EstimatorSlider({
  label,
  hint,
  value,
  max,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  max: number;
  onChange: (n: number) => void;
}) {
  const percent = max === 0 ? 0 : Math.round((value / max) * 100);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-foreground">
          {label}{" "}
          <span className="font-normal text-on-surface-variant">· {hint}</span>
        </span>
        <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
          {value}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={`${label} por mes`}
        className="h-2.5 w-full cursor-pointer appearance-none rounded-full outline-none transition-[background] duration-200 ease-emphasized focus-visible:ring-2 focus-visible:ring-primary/40 [&::-moz-range-thumb]:size-[18px] [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-primary [&::-webkit-slider-thumb]:size-[18px] [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-[0_0_0_4px_color-mix(in_oklab,var(--primary)_22%,transparent)]"
        style={{
          accentColor: "var(--primary)",
          background: `linear-gradient(90deg, var(--primary) 0 ${percent}%, var(--surface-container-highest) ${percent}% 100%)`,
        }}
      />
    </div>
  );
}
