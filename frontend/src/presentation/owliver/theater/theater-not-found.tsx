/**
 * TheaterNotFound — the neutral 404 state for a private scan the viewer can't see
 * (§F6, 12-api). It must NOT confirm whether the scan exists; the copy is generic.
 * Rendered in the SOC palette so it stays in-world with the war room.
 */
import Link from "next/link";

import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { OwlMascot } from "@/src/presentation/owliver/components/owl-mascot";

export function TheaterNotFound() {
  return (
    <div className="soc flex min-h-screen flex-col items-center justify-center gap-5 bg-background px-4 text-center text-foreground">
      <OwlMascot state="idle" size={72} />
      <div>
        <h1 className="font-mono text-2xl font-semibold">Escaneo no encontrado</h1>
        <p className="mt-2 max-w-md text-sm text-on-surface-variant">
          Este escaneo no existe o no tienes acceso a él. Los escaneos privados
          solo son visibles para su propietario.
        </p>
      </div>
      <Link href="/" className={buttonVariants({ variant: "tertiary" })}>
        Volver al inicio
      </Link>
    </div>
  );
}
