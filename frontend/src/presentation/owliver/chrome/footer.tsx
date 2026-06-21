/**
 * Footer — public Owliver closeout. Leads with support + contact (responsible
 * disclosure, ranking review, a direct line to the team) and keeps the
 * legal/passive-scan framing visible. Account access stays reachable as a
 * low-key utility link rather than a prominent CTA block.
 */

import { ArrowUpRight, Mail, MessageSquare, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";
import { OwlMark } from "@/src/presentation/owliver/icons";

export type FooterProps = {
  className?: string;
};

const CONTACT_EMAIL = "contact@llamitai.com";

type FooterLink = {
  href: string;
  label: string;
  external?: boolean;
};

const SUPPORT_LINKS: FooterLink[] = [
  {
    href: `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
      "Reporte de vulnerabilidad"
    )}`,
    label: "Reportar una vulnerabilidad",
    external: true,
  },
  {
    href: `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
      "Revisión de mi sitio en el ranking"
    )}`,
    label: "¿Tu sitio aparece en el ranking?",
    external: true,
  },
  { href: "/", label: "Cómo se calcula la nota A-F" },
];

const TRUST_POINTS = [
  "Datos pasivos y públicos",
  "Lectura A-F verificable",
  "Web + superficie agéntica",
];

function FooterNavLink({ href, label, external }: FooterLink) {
  return (
    <Link
      href={href}
      className="group inline-flex w-fit items-center gap-1 rounded-full py-1 text-on-surface-variant outline-none transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
    >
      {label}
      {external ? (
        <ArrowUpRight className="size-3.5 -translate-x-0.5 text-on-surface-variant/60 opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:text-secondary group-hover:opacity-100 group-focus-visible:translate-x-0 group-focus-visible:opacity-100" />
      ) : null}
    </Link>
  );
}

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: FooterLink[];
}) {
  return (
    <nav aria-label={title} className="space-y-3">
      <p className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
        {title}
      </p>
      <div className="flex flex-col items-start gap-2 text-sm">
        {links.map((link) => (
          <FooterNavLink key={`${link.href}-${link.label}`} {...link} />
        ))}
      </div>
    </nav>
  );
}

export function Footer({ className }: FooterProps) {
  return (
    <footer
      data-slot="owliver-footer"
      className={cn(
        "mt-20 border-t border-outline-variant bg-surface-container-low",
        className
      )}
    >
      <div className="mx-auto max-w-6xl px-4 py-12 md:px-6 md:py-14">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1.3fr]">
          {/* Brand + posture */}
          <div className="sm:col-span-2 lg:col-span-1">
            <BrandLockup size="md" />
            <p className="mt-4 max-w-md text-sm leading-6 text-on-surface-variant">
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

          <FooterColumn title="Soporte" links={SUPPORT_LINKS} />

          {/* Contact — the useful star: a direct, human line to the team */}
          <section
            aria-label="Contacto"
            className="flex flex-col rounded-lg bg-background p-5 sm:col-span-2 lg:col-span-1"
          >
            <p className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
              Contacto
            </p>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="group mt-3 inline-flex w-fit items-center gap-2 rounded-full text-base font-semibold text-foreground outline-none transition-colors hover:text-primary focus-visible:text-primary focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Mail className="size-4 shrink-0 text-primary" />
              <span className="break-all">{CONTACT_EMAIL}</span>
              <ArrowUpRight className="size-4 shrink-0 -translate-x-0.5 opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100 group-focus-visible:translate-x-0 group-focus-visible:opacity-100" />
            </a>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Soporte, divulgación de seguridad y prensa. Escríbenos y hablas
              directo con el equipo de Owliver.
            </p>
            <p className="mt-auto inline-flex items-center gap-2 pt-5 font-mono text-xs font-semibold uppercase tracking-wide text-secondary">
              <MessageSquare className="size-3.5" />
              Sin bots ni tickets
            </p>
          </section>
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t border-outline-variant pt-5 text-xs text-on-surface-variant sm:flex-row sm:items-center sm:justify-between">
          <p className="inline-flex items-center gap-1.5">
            <OwlMark className="size-4 text-primary" /> Owliver ·{" "}
            {new Date().getFullYear()}
          </p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
            <span>Equivalente pasivo a Observatory / SSL Labs / Shodan.</span>
            <Link
              href="/login"
              className="rounded-full font-medium text-on-surface-variant outline-none transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
            >
              Iniciar sesión
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
