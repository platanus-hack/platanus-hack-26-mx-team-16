/**
 * OnboardingView — the first-run guide for a new signed-in user (design
 * `Page · Onboarding`): owl mark, an intro, a 3-step "Primeros pasos" card and
 * the primary CTA into the scan flow. Server component; the only client island is
 * the `OwlMascot` (animation). Lives inside the `(protected)/(owliver)` layout,
 * so the TopNav + Footer chrome comes from there.
 */
import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";

const STEPS = [
  {
    title: "Audita tu primer dominio",
    description:
      "Pega la URL de tu sitio y elige el nivel de auditoría. Owliver hace el resto.",
    badge: "Empieza aquí",
    active: true,
  },
  {
    title: "Revisa tu grado A–F",
    description:
      "Recibe un reporte claro con tus riesgos priorizados y cómo resolverlos.",
    badge: "Pendiente",
  },
  {
    title: "Actívalo en tu watchlist",
    description:
      "Vigila tu sitio en automático y recibe alertas cuando algo cambie.",
    badge: "Pendiente",
  },
];

export function OnboardingView() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-8 px-4 py-16 md:py-20">
      <div className="flex flex-col items-center gap-5 text-center">
        <span className="flex size-20 items-center justify-center rounded-full bg-primary-container">
          <OwlMascot state="idle" size={48} />
        </span>

        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-container px-3 py-1 text-xs font-semibold uppercase tracking-wider text-on-primary-container">
          <Sparkles className="size-3.5" />
          Primer escaneo
        </span>

        <div className="flex flex-col gap-3">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">
            Tu primer escaneo, paso a paso
          </h1>
          <p className="text-balance text-[15px] text-muted-foreground">
            En tres pasos pones tu URL bajo la mirada de Owliver y empiezas a
            vigilar su seguridad en automático.
          </p>
        </div>
      </div>

      {/* Steps */}
      <div className="flex w-full flex-col gap-3 rounded-2xl border border-outline-variant bg-card p-5 md:p-6">
        <div className="flex items-center justify-between px-1">
          <span className="text-sm font-semibold text-foreground">
            Primeros pasos
          </span>
          <span className="text-xs text-outline">0 de 3 completados</span>
        </div>

        {STEPS.map((step, i) => (
          <div
            key={step.title}
            className="flex items-center gap-4 rounded-xl border border-outline-variant bg-surface-container-low px-4 py-4"
          >
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                step.active
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary-container text-on-secondary-container"
              }`}
            >
              {i + 1}
            </span>
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="text-sm font-semibold text-foreground">
                {step.title}
              </span>
              <span className="text-sm text-muted-foreground">
                {step.description}
              </span>
            </div>
            <span
              className={`hidden shrink-0 rounded-full px-3 py-1 text-xs font-medium sm:inline ${
                step.active
                  ? "bg-primary-container text-on-primary-container"
                  : "bg-surface-container text-outline"
              }`}
            >
              {step.badge}
            </span>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center gap-3">
        <Link
          href="/scan"
          className={buttonVariants({ variant: "tertiary", size: "xl" })}
        >
          Auditar mi primer sitio
          <ArrowRight />
        </Link>
        <Link
          href="/"
          className="text-sm text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          o explora el Hall of Shame primero
        </Link>
      </div>
    </div>
  );
}
