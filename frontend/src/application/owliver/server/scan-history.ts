/**
 * Server-only loader for `/scans` — the signed-in user's run history (§F6).
 * Mirrors `loadRankingPage`: an RSC may call `backendGet` directly (CLAUDE.md
 * BFF note).
 *
 * It forwards `GET /v1/scans?limit=100` (the backend filters by the authenticated
 * user and returns rows newest-first), validates the lean list rows with
 * {@link scanListRowSchema} and maps them onto the richer `ScanHistoryItem` the
 * view expects (filling the columns the list presenter omits with safe defaults).
 *
 * Demo fixtures (see {@link fixturesEnabled}, ON by default) are APPENDED AFTER
 * the real runs — so the presentation always shows a populated list even with
 * few/no real scans — and dedup'd by `scanId` so a real run never collides with a
 * demo row. With the flag OFF we serve only real data (and an honest empty list
 * when the backend is unreachable).
 *
 * The order returned here is authoritative recency — the client view re-sorts
 * ONLY when the user picks a different sort.
 */
import "server-only";

import {
  scanHistoryFixture,
  type ScanHistoryItem,
} from "@/src/application/owliver/fixtures";
import { backendGet } from "@/src/application/owliver/lib/bff";
import { parsePage } from "@/src/application/owliver/lib/envelope";
import { fixturesEnabled } from "@/src/application/owliver/lib/fixtures-flag";
import {
  type ScanListRow,
  scanListRowSchema,
} from "@/src/application/owliver/schemas/api";

export type ScanHistory = {
  items: ScanHistoryItem[];
  /** True only when we served PURE fixtures because the backend was unreachable. */
  fromFixture: boolean;
};

/**
 * Lift a lean `GET /scans` row onto the full `ScanHistoryItem` shape the history
 * view renders, defaulting the columns the list presenter does not emit
 * (mirrors the fixture builder's defaults).
 */
function toHistoryItem(row: ScanListRow): ScanHistoryItem {
  return {
    scanId: row.scanId,
    siteId: row.siteId,
    host: row.host ?? "",
    departmentName: row.departmentName ?? null,
    level: row.level,
    visibility: row.visibility,
    status: row.status,
    progress: row.progress ?? 0,
    currentPhase: null,
    webScore: null,
    agenticScore: null,
    overallScore: row.overallScore ?? null,
    overallGrade: row.overallGrade ?? null,
    webGrade: null,
    agenticGrade: null,
    penaltyRaw: null,
    agenticStatus: null,
    toolsStatus: {},
    coverage: [],
    partialCoverage: row.status === "partial",
    error: null,
    startedAt: null,
    finishedAt: row.finishedAt ?? null,
    createdAt: row.createdAt ?? null,
    updatedAt: row.finishedAt ?? row.createdAt ?? null,
    findingsCount: 0,
    criticalCount: 0,
    topFinding: null,
    topFindingSource: "owasp",
    trend: null,
  };
}

/** Demo rows whose `scanId` does not collide with a real run. */
function demoRows(realItems: ScanHistoryItem[]): ScanHistoryItem[] {
  const realIds = new Set(realItems.map((i) => i.scanId));
  return scanHistoryFixture.filter((row) => !realIds.has(row.scanId));
}

export async function loadScanHistory(): Promise<ScanHistory> {
  const withFixtures = fixturesEnabled();
  const result = await backendGet("/scans", { limit: 100 });

  if (result.ok) {
    try {
      const { data } = parsePage(scanListRowSchema, result.data);
      const items = data.map(toHistoryItem);
      // Real runs first, demo history appended (when enabled) so the list is
      // never empty for the presentation.
      const merged = withFixtures ? [...items, ...demoRows(items)] : items;
      return { items: merged, fromFixture: false };
    } catch {
      // Malformed payload — fall through to the fixture path below.
    }
  }

  // Backend unreachable / unauthenticated / contract drift: show the demo
  // history ONLY when the flag is on; otherwise surface an honest empty list.
  return withFixtures
    ? { items: scanHistoryFixture, fromFixture: true }
    : { items: [], fromFixture: false };
}
