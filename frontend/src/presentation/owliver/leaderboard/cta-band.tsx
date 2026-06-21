/**
 * CtaBand — the closing call-to-action below the methodology (§F4). RSC. A
 * primary-container panel that pushes the universal entry point: audit ANY URL,
 * not just gov. Amber "owl-eyes" tertiary button → the scan form (§F5). Uses
 * `buttonVariants` on a `next/link` (Base UI Button has no asChild — chrome
 * pattern).
 */
import Link from "next/link";

import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";

export function CtaBand() {
  return (
    <section className="mt-16">
      <div className="flex flex-col items-center gap-5 rounded-3xl bg-primary-container px-6 py-12 text-center">
        <OwlMascot state="alert" size={56} />
        <h2 className="max-w-xl text-2xl font-semibold tracking-tight text-on-surface md:text-3xl">
          ¿Tu sitio está en la lista? Averígualo.
        </h2>
        <p className="max-w-md text-sm text-on-surface-variant">
          Audita cualquier URL — gobierno o no — en modo pasivo, anónimo y sin
          permisos. El búho hace el resto.
        </p>
        <Link
          href="/scan"
          className={buttonVariants({ variant: "tertiary", size: "xl" })}
        >
          Audita cualquier URL →
        </Link>
      </div>
    </section>
  );
}
