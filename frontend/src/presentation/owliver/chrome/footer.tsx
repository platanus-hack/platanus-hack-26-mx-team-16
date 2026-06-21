/**
 * Footer — public Owliver closeout. Keeps the legal/passive-scan framing visible
 * while giving users clear paths into scanning or their account.
 */

import { LogIn, Radar, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";
import { OwlMark } from "@/src/presentation/owliver/icons";

export type FooterProps = {
  className?: string;
};

const FOOTER_LINKS = [
  { href: "/", label: "Hall of Shame" },
  { href: "/como-funciona", label: "Cómo funciona" },
  { href: "/scan", label: "Auditar URL" },
  { href: "/login", label: "Entrar a cuenta" },
];

const TRUST_POINTS = [
  "Datos pasivos y públicos",
  "Lectura A-F verificable",
  "Web + superficie agéntica",
];

export function Footer({ className }: FooterProps) {
  return (
    <footer
      data-slot="owliver-footer"
      className={cn(
        "mt-20 border-t border-outline-variant bg-surface-container-low",
        className
      )}
    >
      <div className="mx-auto max-w-6xl px-4 py-10 md:px-6 md:py-12">
        <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-start">
          <div className="max-w-2xl">
            <BrandLockup size="md" />
            <p className="mt-4 max-w-xl text-sm leading-6 text-on-surface-variant">
              Owliver convierte señales públicas de seguridad web e IA en una
              lectura operativa: qué falló, qué tan grave es y qué revisar
              primero.
            </p>
            <ul className="mt-5 flex flex-wrap gap-2">
              {TRUST_POINTS.map((point) => (
                <li
                  key={point}
                  className="inline-flex min-h-8 items-center gap-2 rounded-full bg-background px-3 font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant"
                >
                  <ShieldCheck className="size-3.5 text-secondary" />
                  {point}
                </li>
              ))}
            </ul>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:min-w-80">
            <nav aria-label="Pie de página" className="space-y-2">
              <p className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
                Navegación
              </p>
              <div className="flex flex-col items-start gap-2 text-sm">
                {FOOTER_LINKS.map((l) => (
                  <Link
                    key={l.href}
                    href={l.href}
                    className="rounded-full py-1 text-on-surface-variant outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {l.label}
                  </Link>
                ))}
              </div>
            </nav>

            <div className="space-y-3">
              <p className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
                Acceso
              </p>
              <Link
                href="/scan"
                className={buttonVariants({ variant: "default", size: "sm" })}
              >
                <Radar className="size-4" />
                Auditar URL
              </Link>
              <Link
                href="/login"
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                  "ml-2"
                )}
              >
                <LogIn className="size-4" />
                Entrar
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-outline-variant pt-5 text-xs text-on-surface-variant sm:flex-row sm:items-center sm:justify-between">
          <p className="inline-flex items-center gap-1.5">
            <OwlMark className="size-4 text-primary" /> Owliver por Llamitai ·{" "}
            {new Date().getFullYear()}
          </p>
          <p>Equivalente pasivo a Observatory / SSL Labs / Shodan.</p>
        </div>
      </div>
    </footer>
  );
}
