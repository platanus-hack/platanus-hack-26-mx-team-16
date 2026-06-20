import { redirect } from "next/navigation";

/**
 * Re-IA 2026-06 (brief workflow-detail-ia): la raíz del workflow aterriza
 * directo en Casos — la única entidad operativa. El hub interstitial de cards
 * («elige a dónde ir») duplicaba el sidebar sin aportar datos y costaba una
 * decisión extra por visita.
 */
export default async function WorkflowRootPage({
  params,
}: {
  params: Promise<{ wfSlug: string }>;
}) {
  const { wfSlug } = await params;
  redirect(`/workflows/${wfSlug}/cases`);
}
