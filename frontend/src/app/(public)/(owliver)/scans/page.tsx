/**
 * `/scans` — Mis escaneos (§F6). The signed-in user's run history: the index that
 * sits beside the existing `scans/[id]` (live theater) and `scans/[id]/report`
 * (full report) routes. RSC shell — it loads the authoritative recency-ordered
 * history (`loadScanHistory`, fixture fallback offline) and hands it to the
 * client `ScanHistoryView`, which owns search / filter / sort and the entrance
 * stagger. Rows route out to the report (finished) or theater (in-flight).
 *
 * Lives in the (owliver) public shell so it wears the same TopNav + Footer; the
 * layout already surfaces "Mi Cuenta" + the session-only nav when logged in.
 */
import type { Metadata } from "next";

import { loadScanHistory } from "@/src/application/owliver/server/scan-history";
import { ScanHistoryView } from "@/src/presentation/owliver/scans/scan-history-view";

export const metadata: Metadata = {
  title: "Mis escaneos",
  description:
    "El historial de tus auditorías de seguridad en Owliver: grado A–F, hallazgos y el reporte completo de cada ejecución.",
};

// Always render fresh server data (the list hydrates from here).
export const dynamic = "force-dynamic";

export default async function ScansPage() {
  const { items } = await loadScanHistory();
  return <ScanHistoryView items={items} />;
}
