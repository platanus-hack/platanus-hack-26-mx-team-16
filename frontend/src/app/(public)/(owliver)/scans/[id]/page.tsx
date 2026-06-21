/**
 * `/scans/[id]` — ★ Live Pentest Theater (§F6), the centerpiece. RSC shell that
 * seeds the initial scan state server-side (`backendGet /scans/{id}`, fixture
 * fallback for the offline demo) and hands it to the client `TheaterView`, which
 * opens the SSE stream and paints the war room.
 *
 * A 404 from the backend (private scan without permission) renders a neutral
 * "no encontrado" page — we must NOT confirm the scan exists (12-api). The SOC
 * theater renders its own full-bleed dark frame inside the public shell.
 */
import type { Metadata } from "next";

import {
  findScanFixtureById,
  scanFixture,
} from "@/src/application/owliver/fixtures";
import { backendGet } from "@/src/application/owliver/lib/bff";
import { parseData } from "@/src/application/owliver/lib/envelope";
import { scanSchema, type Scan } from "@/src/application/owliver/schemas/api";
import { TheaterView } from "@/src/presentation/owliver/theater/theater-view";
import { TheaterNotFound } from "@/src/presentation/owliver/theater/theater-not-found";

export const metadata: Metadata = {
  title: "Escaneo en vivo",
  description: "Pentest automatizado en tiempo real.",
};

async function loadScan(
  id: string
): Promise<{ scan: Scan } | { notFound: true }> {
  const result = await backendGet(`/scans/${id}`);

  if (result.ok) {
    try {
      return { scan: parseData(scanSchema, result.data) };
    } catch {
      // Contract drift → fall back to the demo scan so the theater still plays.
      return { scan: scanFixture };
    }
  }
  // 404 = private scan / no permission → do not confirm existence.
  if (result.status === 404) return { notFound: true };

  // Backend unreachable (no live worker in the demo) → fixture replay.
  return { scan: scanFixture };
}

export default async function TheaterPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const loaded = await loadScan(id);

  if ("notFound" in loaded) {
    return <TheaterNotFound />;
  }

  return <TheaterView scanId={id} initialScan={loaded.scan} />;
}
