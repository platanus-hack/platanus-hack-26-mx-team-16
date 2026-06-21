/**
 * Footer — the public Owliver footer (§F3/§F8). Carries the brand mark, the
 * closing tagline ("Owliver vigila la seguridad del Estado y de tu IA…"), the
 * legal-defensibility microcopy (passive/public data framing — 01-legal-ethics),
 * and quiet links. Theme-aware; appears on every (public) page below the content.
 */
import Link from "next/link";

import { cn } from "@/src/application/lib/utils";
import { BrandLockup } from "@/src/presentation/owliver/chrome/brand-lockup";
import { OwlMark } from "@/src/presentation/owliver/icons";

export type FooterProps = {
  className?: string;
};

const FOOTER_LINKS = [
  { href: "/", label: "Hall of Shame" },
  { href: "/scan", label: "Auditar URL" },
  { href: "/como-funciona", label: "Cómo Funciona" },
  { href: "/login", label: "Iniciar sesión" },
];

export function Footer({ className }: FooterProps) {
  return (
    <footer
      data-slot="owliver-footer"
      className={cn(
        "mt-16 border-t border-outline-variant bg-surface-container-low",
        className
      )}
    >
      <div className="mx-auto max-w-6xl px-4 py-10 md:px-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-md space-y-3">
            <BrandLockup size="sm" />
            <p className="text-sm text-on-surface-variant">
              Owliver vigila la seguridad del Estado y de tu IA — lo que nadie
              más está midiendo.
            </p>
            <p className="text-xs text-on-surface-variant/80">
              Datos 100% pasivos y públicos — equivalente a Mozilla Observatory
              / SSL Labs / Shodan. No intrusivo.
            </p>
          </div>

          <nav
            className="flex flex-col gap-2 text-sm"
            aria-label="Pie de página"
          >
            {FOOTER_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-on-surface-variant transition-colors hover:text-foreground"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>

        <p className="mt-8 inline-flex items-center gap-1.5 text-xs text-on-surface-variant/70">
          <OwlMark className="size-4" /> Owliver por Llamitai ·{" "}
          {new Date().getFullYear()}
        </p>
      </div>
    </footer>
  );
}
