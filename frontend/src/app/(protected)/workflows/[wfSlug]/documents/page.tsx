"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * Re-IA 2026-06 (brief workflow-detail-ia): la lista global de runs técnicos
 * («Documents») salió de la navegación — los runs de procesamiento viven en la
 * tab Actividad de cada caso, y la lista de Casos filtra «Con errores».
 * Redirect para que links/bookmarks viejos no rompan. El detalle de documento
 * (`/documents/[documentId]`) sigue vivo: es el bench de revisión.
 */
export default function WorkflowDocumentsRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const wfSlug = params.wfSlug as string;

  useEffect(() => {
    if (wfSlug) {
      router.replace(`/workflows/${wfSlug}/cases`);
    }
  }, [wfSlug, router]);

  return null;
}
