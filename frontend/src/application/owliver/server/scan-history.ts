/**
 * Server-only loader for `/scans` — the signed-in user's run history (§F6).
 * Mirrors `loadRankingPage`: an RSC may call `backendGet` directly (CLAUDE.md
 * BFF note) and we fall back to the fixture so the page renders from hour 2.
 *
 * When the backend lands this forwards `GET /v1/scans?mine=1` (newest first) and
 * validates the rows; for now it serves the fixture. The order returned here is
 * authoritative recency — the client view re-sorts ONLY when the user picks a
 * different sort.
 */
import "server-only";

import {
  scanHistoryFixture,
  type ScanHistoryItem,
} from "@/src/application/owliver/fixtures";

export type ScanHistory = {
  items: ScanHistoryItem[];
  /** True when we served fixtures (no live backend). */
  fromFixture: boolean;
};

export async function loadScanHistory(): Promise<ScanHistory> {
  // Backend not wired yet — serve the demo history so the screen always paints.
  return { items: scanHistoryFixture, fromFixture: true };
}
