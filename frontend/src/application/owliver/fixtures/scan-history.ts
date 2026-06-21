/**
 * Scan-history fixtures (§F6) — the signed-in user's run log for `/scans`.
 *
 * The frozen contract ships only ONE live scan (`scanFixture`); the history list
 * needs many — across every status, grade, level and coverage state — so the
 * page, its filters, time-grouping and the empty / running / failed states all
 * render without a backend ("funcionando contra fixtures desde la hora 2", §F15).
 * The first row reuses `HERO_SCAN_ID`, so clicking through lands on the rich demo
 * report fixture at `/scans/{id}/report`.
 */
import type {
  AgenticStatus,
  Grade,
  Scan,
  ScanLevel,
  ScanStatus,
  Trend,
} from "../schemas/api";
import { HERO_SCAN_ID, HERO_SITE_ID } from "./scan";

/**
 * A row in the history list: the authoritative `Scan` plus the small,
 * display-only aggregates the list surfaces — the finding counts, the "why"
 * one-liner and the ▲▼ trend vs the site's previous scan. These extend the scan
 * contract for the list view only; the report and theater still read the
 * canonical `Scan`.
 */
export type ScanHistoryItem = Scan & {
  /** Organization / site display name for the row title. */
  departmentName?: string | null;
  /** Total findings for the row summary (0 while queued/running/failed). */
  findingsCount: number;
  /** Of those, how many are critical (drives the red accent). */
  criticalCount: number;
  /** Top finding one-liner, revealed on hover (the "why"). */
  topFinding?: string | null;
  /** ▲▼ vs the site's previous scan (display only). */
  trend?: Trend | null;
};

const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;
/** Typical scan wall-time so `startedAt` precedes `finishedAt` realistically. */
const RUN_MS = 82_000;

type Seed = {
  scanId: string;
  siteId: string;
  host: string;
  departmentName: string;
  level: ScanLevel;
  status: ScanStatus;
  /** Age of the row's reference timestamp (finished / started / created). */
  ago: number;
  progress?: number;
  currentPhase?: string | null;
  webScore?: number | null;
  agenticScore?: number | null;
  overallScore?: number | null;
  overallGrade?: Grade | null;
  webGrade?: Grade | null;
  agenticGrade?: Grade | null;
  agenticStatus?: AgenticStatus | null;
  partialCoverage?: boolean;
  penaltyRaw?: number | null;
  error?: string | null;
  findingsCount?: number;
  criticalCount?: number;
  topFinding?: string | null;
  trend?: Trend | null;
};

const TERMINAL: ReadonlySet<ScanStatus> = new Set([
  "done",
  "partial",
  "failed",
  "cancelled",
]);

function build(seed: Seed): ScanHistoryItem {
  const now = Date.now();
  const isTerminal = TERMINAL.has(seed.status);

  let startedAt: string | null = null;
  let finishedAt: string | null = null;
  if (isTerminal) {
    finishedAt = new Date(now - seed.ago).toISOString();
    startedAt = new Date(now - seed.ago - RUN_MS).toISOString();
  } else if (seed.status === "running") {
    startedAt = new Date(now - seed.ago).toISOString();
  }
  const createdAt = new Date(
    now - seed.ago - (seed.status === "queued" ? 0 : RUN_MS) - 30_000
  ).toISOString();

  return {
    scanId: seed.scanId,
    siteId: seed.siteId,
    host: seed.host,
    departmentName: seed.departmentName,
    level: seed.level,
    visibility: "private",
    status: seed.status,
    progress: seed.progress ?? (isTerminal ? 100 : 0),
    currentPhase: seed.currentPhase ?? null,
    webScore: seed.webScore ?? null,
    agenticScore: seed.agenticScore ?? null,
    overallScore: seed.overallScore ?? null,
    overallGrade: seed.overallGrade ?? null,
    webGrade: seed.webGrade ?? null,
    agenticGrade: seed.agenticGrade ?? null,
    penaltyRaw: seed.penaltyRaw ?? null,
    agenticStatus: seed.agenticStatus ?? null,
    toolsStatus: {},
    coverage: [],
    partialCoverage: seed.partialCoverage ?? false,
    error: seed.error ?? null,
    startedAt,
    finishedAt,
    createdAt,
    updatedAt: finishedAt ?? startedAt ?? createdAt,
    findingsCount: seed.findingsCount ?? 0,
    criticalCount: seed.criticalCount ?? 0,
    topFinding: seed.topFinding ?? null,
    trend: seed.trend ?? null,
  };
}

/** The user's runs, newest first (the loader/view preserves recency order). */
export const scanHistoryFixture: ScanHistoryItem[] = [
  // ── Hoy ──────────────────────────────────────────────────────────────
  build({
    scanId: "scan-salud-running-0007",
    siteId: "site-salud-gob-mx",
    host: "salud.gob.mx",
    departmentName: "Secretaría de Salud",
    level: "avanzado",
    status: "running",
    ago: 2 * MIN,
    progress: 64,
    currentPhase: "Sondeando el asistente de citas…",
    agenticStatus: "tested",
  }),
  build({
    scanId: HERO_SCAN_ID,
    siteId: HERO_SITE_ID,
    host: "fabrikam.com",
    departmentName: "Fabrikam, Inc.",
    level: "basico",
    status: "done",
    ago: 22 * MIN,
    webScore: 72,
    agenticScore: 24,
    overallGrade: "E",
    webGrade: "C",
    agenticGrade: "F",
    agenticStatus: "tested",
    penaltyRaw: 119,
    findingsCount: 5,
    criticalCount: 1,
    topFinding: "Fuga de system-prompt del asistente vía inyección de prompt",
    trend: "down",
  }),
  build({
    scanId: "scan-mitienda-queued-0009",
    siteId: "site-mitienda-mx",
    host: "mi-tienda.mx",
    departmentName: "Mi Tienda Online",
    level: "intermedio",
    status: "queued",
    ago: 38 * MIN,
  }),

  // ── Esta semana ──────────────────────────────────────────────────────
  build({
    scanId: "scan-tesoreria-0021",
    siteId: "site-tesoreria-gob-mx",
    host: "tesoreria.gob.mx",
    departmentName: "Tesorería de la Federación",
    level: "intermedio",
    status: "done",
    ago: DAY + 3 * HOUR,
    webScore: 38,
    overallGrade: "F",
    webGrade: "F",
    agenticStatus: "no_surface",
    penaltyRaw: 146,
    findingsCount: 11,
    criticalCount: 2,
    topFinding: "Panel administrativo expuesto sin autenticación",
    trend: "down",
  }),
  build({
    scanId: "scan-educacion-0033",
    siteId: "site-educacion-gob-mx",
    host: "educacion.gob.mx",
    departmentName: "Secretaría de Educación Pública",
    level: "basico",
    status: "partial",
    ago: 2 * DAY,
    webScore: 70,
    overallGrade: "C",
    webGrade: "C",
    agenticStatus: "detected_not_tested",
    partialCoverage: true,
    penaltyRaw: 58,
    findingsCount: 4,
    criticalCount: 0,
    topFinding: "Cobertura parcial: ZAP agotó el tiempo en el escaneo activo",
    trend: "flat",
  }),
  build({
    scanId: "scan-sat-failed-0040",
    siteId: "site-sat-gob-mx",
    host: "pagos.sat.gob.mx",
    departmentName: "Servicio de Administración Tributaria",
    level: "avanzado",
    status: "failed",
    ago: 3 * DAY,
    error: "El objetivo cerró la conexión durante el handshake TLS (timeout).",
  }),
  build({
    scanId: "scan-datos-0051",
    siteId: "site-datos-gob-mx",
    host: "datos.gob.mx",
    departmentName: "Datos Abiertos México",
    level: "basico",
    status: "done",
    ago: 5 * DAY,
    webScore: 84,
    agenticScore: 88,
    overallGrade: "B",
    webGrade: "B",
    agenticGrade: "B",
    agenticStatus: "tested",
    penaltyRaw: 24,
    findingsCount: 2,
    criticalCount: 0,
    topFinding: "Cabecera HSTS emitida sin preload",
    trend: "up",
  }),

  // ── Anteriores ───────────────────────────────────────────────────────
  build({
    scanId: "scan-imss-0062",
    siteId: "site-imss-gob-mx",
    host: "portal.imss.gob.mx",
    departmentName: "IMSS — Portal Institucional",
    level: "intermedio",
    status: "done",
    ago: 9 * DAY,
    webScore: 95,
    agenticScore: 92,
    overallGrade: "A",
    webGrade: "A",
    agenticGrade: "A",
    agenticStatus: "tested",
    penaltyRaw: 8,
    findingsCount: 1,
    criticalCount: 0,
    topFinding: "Solo hallazgos informativos — sin acción requerida",
    trend: "up",
  }),
  build({
    scanId: "scan-cdmx-0070",
    siteId: "site-cdmx-tramites",
    host: "tramites.cdmx.gob.mx",
    departmentName: "Trámites CDMX",
    level: "basico",
    status: "done",
    ago: 14 * DAY,
    webScore: 63,
    overallGrade: "D",
    webGrade: "D",
    agenticStatus: "no_surface",
    penaltyRaw: 79,
    findingsCount: 6,
    criticalCount: 1,
    topFinding: "Formulario de trámite sin protección CSRF",
    trend: "flat",
  }),
  build({
    scanId: "scan-banxico-0088",
    siteId: "site-banxico",
    host: "banxico.org.mx",
    departmentName: "Banco de México",
    level: "intermedio",
    status: "done",
    ago: 21 * DAY,
    webScore: 66,
    agenticScore: 54,
    overallGrade: "D",
    webGrade: "D",
    agenticGrade: "E",
    agenticStatus: "tested",
    penaltyRaw: 72,
    findingsCount: 5,
    criticalCount: 0,
    topFinding: "El asistente revela la versión del modelo ante un sondeo",
    trend: "down",
  }),
];
