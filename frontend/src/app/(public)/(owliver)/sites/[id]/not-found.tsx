/**
 * 404 for `/sites/[id]` (§F12). We do NOT confirm whether a site exists — the
 * copy is deliberately generic.
 */
import Link from "next/link";

import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";

export default function SiteNotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-24 text-center">
      <OwlMascot state="idle" size={72} />
      <h1 className="mt-6 text-2xl font-semibold text-foreground">
        No encontramos ese sitio
      </h1>
      <p className="mt-2 text-sm text-on-surface-variant">
        El enlace puede ser incorrecto o el sitio aún no ha sido auditado.
      </p>
      <Link
        href="/"
        className="mt-6 text-sm font-medium text-primary hover:underline"
      >
        Volver al leaderboard
      </Link>
    </div>
  );
}
