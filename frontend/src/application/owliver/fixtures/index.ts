/**
 * Owliver fixtures barrel — every screen renders against these so the UI works
 * without a live backend (§F15: "funcionando contra fixtures desde la hora 2").
 *
 * Import individual fixtures by name, e.g.:
 *   import { rankingFixture } from "@/src/application/owliver/fixtures";
 */
export { rankingFixture, heroRow } from "./ranking";
export {
  HERO_SCAN_ID,
  HERO_SITE_ID,
  scanFixture,
  surfacesFixture,
  findingsFixture,
  reportFixture,
  publicReportFixture,
} from "./scan";
export {
  scanHistoryFixture,
  findScanFixtureById,
  buildReportFixtureFor,
  buildScanEventsFor,
  type ScanHistoryItem,
} from "./scan-history";
export { scanEventsFixture, scanEventsAsSSEWire } from "./scan-events";
export { siteFixture } from "./site";
export { watchlistFixture, alertPrefsFixture } from "./watchlist";
