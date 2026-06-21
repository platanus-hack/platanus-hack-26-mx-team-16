/**
 * Watchlist fixture (§F11) — private monitored domains. `id` is the
 * watchlist-ROW uuid (used for PATCH/DELETE), distinct from `siteId`. Includes a
 * mix of monitor on/off and agentic states. Empty state is handled by the screen.
 */
import type { AlertPrefs, WatchlistRow } from "../schemas/api";

export const watchlistFixture: WatchlistRow[] = [
  {
    id: "wl-row-0001",
    siteId: "site-acme-mx",
    host: "acme.com.mx",
    departmentName: "ACME Servicios",
    overallGrade: "C",
    webGrade: "B",
    agenticGrade: "D",
    agenticStatus: "tested",
    monitor: true,
    lastScanAt: new Date(Date.now() - 2 * 86_400_000).toISOString(),
  },
  {
    id: "wl-row-0002",
    siteId: "site-tienda-acme",
    host: "tienda.acme.com.mx",
    departmentName: "Tienda ACME",
    overallGrade: "D",
    webGrade: "D",
    agenticGrade: null,
    agenticStatus: "detected_not_tested",
    monitor: true,
    lastScanAt: new Date(Date.now() - 5 * 86_400_000).toISOString(),
  },
  {
    id: "wl-row-0003",
    siteId: "site-blog-acme",
    host: "blog.acme.com.mx",
    departmentName: "Blog ACME",
    overallGrade: "B",
    webGrade: "B",
    agenticGrade: null,
    agenticStatus: "no_surface",
    monitor: false,
    lastScanAt: new Date(Date.now() - 12 * 86_400_000).toISOString(),
  },
  {
    id: "wl-row-0004",
    siteId: "site-api-acme",
    host: "api.acme.com.mx",
    departmentName: "API ACME",
    overallGrade: null,
    webGrade: null,
    agenticGrade: null,
    agenticStatus: "no_surface",
    monitor: false,
    lastScanAt: null,
  },
];

export const alertPrefsFixture: AlertPrefs = {
  emailEnabled: true,
  slackWebhookUrl: null,
};
