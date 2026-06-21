/**
 * `/scan` (§F5) — Form de escaneo + gate de atestación. Universal entry point:
 * URL + level. RSC shell (hero copy) wrapping the client <ScanForm>. Inherits
 * the Owliver chrome (TopNav + Footer) from (public)/(owliver)/layout.tsx.
 *
 * The form is also mountable as a modal from `/` via <ScanFormDialog>.
 */
import type { Metadata } from "next";

import { extractHost } from "@/src/application/owliver/lib/url";
import { Reveal } from "@/src/presentation/components/common/reveal";
import { Card, CardContent } from "@/src/presentation/components/ui/card";
import { ScanForm } from "@/src/presentation/owliver/scan/scan-form";

export const metadata: Metadata = {
  title: "Auditar un sitio · Owliver",
  description:
    "Ingresa una URL y elige el nivel de auditoría. Owliver escanea OWASP web + la superficie agéntica (chatbots e IA).",
};

export default async function ScanPage({
  searchParams,
}: {
  searchParams: Promise<{ url?: string }>;
}) {
  // Deep link (e.g. watchlist "Re-escanear" → /scan?url=<host>). Normalize via
  // the shared host helper so we only seed a clean, parseable value.
  const { url } = await searchParams;
  const initialUrl = url ? (extractHost(url) ?? undefined) : undefined;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 md:px-6 md:py-14">
      <Reveal>
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
            Audita cualquier sitio
          </h1>
          <p className="mx-auto mt-3 max-w-lg text-on-surface-variant">
            Owliver revisa la seguridad web (OWASP) y la superficie agéntica —
            chatbots y cajas de IA — buscando lo que casi nadie mide.
          </p>
        </header>
      </Reveal>

      <Reveal delay={80}>
        <Card className="rounded-3xl">
          <CardContent className="p-6 md:p-8">
            <ScanForm initialUrl={initialUrl} />
          </CardContent>
        </Card>
      </Reveal>

      <p className="mx-auto mt-6 max-w-md text-center text-xs text-on-surface-variant/80">
        El nivel <span className="font-medium">Básico</span> es pasivo, anónimo y
        no intrusivo — equivalente a Mozilla Observatory / SSL Labs. Los niveles
        activos requieren tu autorización.
      </p>
    </div>
  );
}
