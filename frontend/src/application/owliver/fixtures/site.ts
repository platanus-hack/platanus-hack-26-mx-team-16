/**
 * Site history fixture (§F9) — the SAT domain over time, the click-destination
 * from a leaderboard row. Includes a grade timeline (oldest → newest) for the
 * trend chart, the latest scan summary, and the detected agentic surface.
 */
import type { ScanHistoryEntry, Site } from "../schemas/api";
import { SAT_SITE_ID, scanFixture, surfacesFixture } from "./scan";

const history: ScanHistoryEntry[] = [
  { scanId: "scan-sat-h1", overallGrade: "D", webScore: 66, agenticScore: 41, scannedAt: new Date(Date.now() - 90 * 86_400_000).toISOString() },
  { scanId: "scan-sat-h2", overallGrade: "D", webScore: 68, agenticScore: 38, scannedAt: new Date(Date.now() - 60 * 86_400_000).toISOString() },
  { scanId: "scan-sat-h3", overallGrade: "E", webScore: 70, agenticScore: 30, scannedAt: new Date(Date.now() - 30 * 86_400_000).toISOString() },
  { scanId: "scan-sat-h4", overallGrade: "E", webScore: 71, agenticScore: 27, scannedAt: new Date(Date.now() - 7 * 86_400_000).toISOString() },
  { scanId: scanFixture.id, overallGrade: "E", webScore: 72, agenticScore: 24, scannedAt: new Date().toISOString() },
];

export const siteFixture: Site = {
  id: SAT_SITE_ID,
  host: "sat.gob.mx",
  departmentName: "Servicio de Administración Tributaria",
  isGov: true,
  faviconUrl: "https://www.google.com/s2/favicons?domain=sat.gob.mx&sz=64",
  latestScan: scanFixture,
  history,
  surfaces: surfacesFixture,
};
