/**
 * 404 for `/r/[token]` (§F8/§F12). A missing share token does NOT confirm
 * whether a report ever existed — the copy is deliberately generic. (Expired /
 * revoked tokens return 410 and render the "enlace expiró" state in page.tsx.)
 */
import Link from "next/link";

import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";

export default function PublicReportNotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-24 text-center">
      <OwlMascot state="idle" size={72} />
      <h1 className="mt-6 text-2xl font-semibold text-foreground">
        Enlace no encontrado
      </h1>
      <p className="mt-2 text-sm text-on-surface-variant">
        Este enlace público no es válido o ya no está disponible.
      </p>
      <Link
        href="/"
        className="mt-6 text-sm font-medium text-primary hover:underline"
      >
        Ir al inicio
      </Link>
    </div>
  );
}
