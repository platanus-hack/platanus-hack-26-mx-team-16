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
  AgenticSurface,
  Finding,
  Grade,
  Report,
  Scan,
  ScanLevel,
  ScanStatus,
  Severity,
  Source,
  Trend,
} from "../schemas/api";
import type { ScanEvent } from "../schemas/sse";
import { HERO_SCAN_ID, HERO_SITE_ID, reportFixture } from "./scan";
import { scanEventsFixture } from "./scan-events";

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
  /** Lane the topFinding belongs to, so the synthesized lead finding (report +
   * live) is attributed to the right tool/category. Defaults to "owasp". */
  topFindingSource?: Source | null;
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
  topFindingSource?: Source;
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
    topFindingSource: seed.topFindingSource ?? "owasp",
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
    topFindingSource: "agentic",
    trend: "down",
  }),
];

// ─── By-id resolvers (offline fixture fallback) ──────────────────────────────
//
// The detail surfaces — the live theater (`/scans/{id}`) and the report
// (`/scans/{id}/report`) — fall back to fixtures when the backend is unreachable.
// Resolving them BY ID (instead of always returning the single hero fixture)
// means clicking ANY row in `/scans` opens data that matches that row: the right
// host, grade, level and links. Each history row already IS a full `Scan`, so the
// theater seed is a direct lookup; the report is synthesized from the same row.

const HISTORY_BY_ID: ReadonlyMap<string, ScanHistoryItem> = new Map(
  scanHistoryFixture.map((item) => [item.scanId, item])
);

/** The demo `Scan` for an id (the theater seed). `undefined` → unknown id. */
export function findScanFixtureById(id: string): Scan | undefined {
  return HISTORY_BY_ID.get(id);
}

function findingsLabel(n: number): string {
  return `${n} ${n === 1 ? "hallazgo" : "hallazgos"}`;
}

function explanationFor(item: ScanHistoryItem): string {
  const name = item.departmentName ?? item.host;
  const parts = [
    `Owliver auditó ${item.host} (${name}) en nivel ${item.level}.`,
  ];
  if (item.criticalCount > 0) {
    parts.push(
      item.criticalCount === 1
        ? "Se encontró 1 hallazgo crítico que requiere atención inmediata."
        : `Se encontraron ${item.criticalCount} hallazgos críticos que requieren atención inmediata.`
    );
  }
  parts.push(
    item.agenticStatus === "tested"
      ? "Su superficie agéntica (chatbots / cajas de IA) fue auditada."
      : item.agenticStatus === "detected_not_tested"
        ? "Se detectó una superficie de IA que no alcanzó a auditarse."
        : "No se detectó superficie agéntica."
  );
  if (item.overallGrade) {
    parts.push(
      `Sobre la base de ${findingsLabel(item.findingsCount)}, el sitio obtiene un grado global ${item.overallGrade}.`
    );
  }
  return parts.join(" ");
}

function surfacesFor(item: ScanHistoryItem): AgenticSurface[] {
  if (
    item.agenticStatus !== "tested" &&
    item.agenticStatus !== "detected_not_tested"
  ) {
    return [];
  }
  return [
    {
      type: "chatbot",
      vendor: null,
      locationUrl: `https://${item.host}/asistente`,
      inferredModel:
        item.agenticStatus === "tested" ? "modelo no expuesto" : null,
      agenticStatus: item.agenticStatus,
    },
  ];
}

/** Severity rota used to fill a row's report after its criticals (descending). */
const FINDING_TEMPLATES: {
  severity: Severity;
  source: Source;
  tool: string;
  category: string;
  cvss: number | null;
  title: string;
  impact: string;
  remediation: string;
  references: string[];
}[] = [
  {
    severity: "high",
    source: "owasp",
    tool: "testssl",
    category: "A02",
    cvss: 7.3,
    title: "Protocolos TLS obsoletos habilitados",
    impact:
      "El tráfico de los usuarios puede interceptarse mediante un ataque de degradación.",
    remediation:
      "Deshabilitar TLS 1.0/1.1 y exigir TLS 1.2+ con cifrados modernos (AEAD).",
    references: ["OWASP-A02", "CWE-326"],
  },
  {
    severity: "medium",
    source: "owasp",
    tool: "nuclei",
    category: "A05",
    cvss: 5.3,
    title: "Cabeceras de seguridad ausentes (CSP, HSTS, X-Frame-Options)",
    impact: "El sitio queda expuesto a clickjacking e inyección de contenido.",
    remediation:
      "Agregar CSP estricta, HSTS con preload y X-Frame-Options DENY.",
    references: ["OWASP-A05", "CWE-693"],
  },
  {
    severity: "low",
    source: "owasp",
    tool: "zap",
    category: "A05",
    cvss: 3.1,
    title: "Cookie de sesión sin atributo Secure",
    impact: "La cookie podría viajar por una conexión no cifrada.",
    remediation: "Agregar el atributo Secure (y SameSite=Strict cuando aplique).",
    references: ["OWASP-A05", "CWE-614"],
  },
  {
    severity: "info",
    source: "owasp",
    tool: "zap",
    category: "INFO",
    cvss: null,
    title: "Nota de cobertura del escaneo",
    impact: "Sin impacto de seguridad; nota informativa de cobertura.",
    remediation:
      "Ejecutar un nivel activo (con autorización) para cobertura completa.",
    references: [],
  },
];

/** Where to enter the severity rota (high→info) so it tracks the grade. */
function fillerStartIndex(grade: Grade | null | undefined): number {
  switch (grade) {
    case "A":
      return 3; // info
    case "B":
      return 2; // low
    case "C":
      return 1; // medium
    default:
      return 0; // high (D/E/F or ungraded)
  }
}

/** A lead finding attributed to the agentic lane (prompt-injection probe). */
function makeAgenticFinding(
  item: ScanHistoryItem,
  id: string,
  severity: Severity
): Finding {
  return {
    id,
    source: "agentic",
    tool: "promptfoo",
    category: "LLM01",
    title: item.topFinding ?? "El asistente de IA respondió de forma insegura",
    severity,
    cvss: severity === "critical" ? 9.1 : 7.5,
    confidence: "alta",
    description: `El asistente de IA de ${item.host} respondió de forma insegura ante las sondas de inyección de prompt de Owliver.`,
    evidence: {},
    affectedUrl: `https://${item.host}/asistente`,
    endpoint: "/asistente/chat",
    param: "message",
    impact:
      "Permite mapear las restricciones del asistente y diseñar jailbreaks dirigidos para obtener respuestas no autorizadas en nombre de la marca.",
    remediation:
      "Aislar el system-prompt del contexto del usuario y aplicar filtros de salida que detecten fugas de prompt o jailbreaks.",
    references: ["OWASP-LLM01", "CWE-200"],
  };
}

function findingsFor(item: ScanHistoryItem): Finding[] {
  const total = item.findingsCount;
  if (total <= 0) return [];

  const findings: Finding[] = [];
  // When the row's "why" is an agentic finding, the lead is attributed to the
  // agentic lane (LLM01/promptfoo) — not OWASP/nuclei.
  const agenticLead = item.topFindingSource === "agentic" && !!item.topFinding;

  // Criticals first — the row's `topFinding` leads the list when present.
  for (let i = 0; i < item.criticalCount && findings.length < total; i++) {
    if (i === 0 && agenticLead) {
      findings.push(
        makeAgenticFinding(item, `${item.scanId}-f-${findings.length}`, "critical")
      );
      continue;
    }
    findings.push({
      id: `${item.scanId}-f-${findings.length}`,
      source: "owasp",
      tool: "nuclei",
      category: "A01",
      title:
        i === 0 && item.topFinding
          ? item.topFinding
          : "Hallazgo crítico de control de acceso",
      severity: "critical",
      cvss: 9.1,
      confidence: "alta",
      description: `Owliver confirmó un riesgo crítico en ${item.host} durante la auditoría de nivel ${item.level}.`,
      evidence: {},
      affectedUrl: `https://${item.host}`,
      impact:
        "Compromete directamente la confidencialidad o la integridad del sitio.",
      remediation:
        "Corregir de inmediato y volver a auditar para confirmar la mitigación.",
      references: ["OWASP-A01", "CWE-284"],
    });
  }

  // Fill the rest by cycling the severity rota; `topFinding` leads if no critical.
  // Start the rota at a severity that matches the grade so a clean A/B scan does
  // not synthesize a "high" finding (FINDING_TEMPLATES is ordered high → info).
  const start = fillerStartIndex(item.overallGrade);
  let t = 0;
  while (findings.length < total) {
    const tpl = FINDING_TEMPLATES[(start + t) % FINDING_TEMPLATES.length];
    if (findings.length === 0 && agenticLead) {
      findings.push(
        makeAgenticFinding(item, `${item.scanId}-f-${findings.length}`, tpl.severity)
      );
      t++;
      continue;
    }
    const lead =
      findings.length === 0 && item.topFinding ? item.topFinding : null;
    const title =
      lead ?? (t >= FINDING_TEMPLATES.length ? `${tpl.title} (${t + 1})` : tpl.title);
    findings.push({
      id: `${item.scanId}-f-${findings.length}`,
      source: tpl.source,
      tool: tpl.tool,
      category: tpl.category,
      title,
      severity: tpl.severity,
      cvss: tpl.cvss,
      confidence: "alta",
      description: `${tpl.title} detectada en ${item.host}.`,
      evidence: {},
      affectedUrl: `https://${item.host}`,
      impact: tpl.impact,
      remediation: tpl.remediation,
      references: tpl.references,
    });
    t++;
  }

  return findings;
}

/**
 * The demo `Report` for an id (offline fallback). The hand-authored hero report
 * stays rich; every other row gets a report synthesized from its OWN data so the
 * page shows the scan the user actually clicked — not a stand-in. Unknown ids
 * fall back to the hero report.
 */
export function buildReportFixtureFor(id: string): Report {
  if (id === HERO_SCAN_ID) return reportFixture;
  const item = HISTORY_BY_ID.get(id);
  if (!item) return reportFixture;

  const findings = findingsFor(item);
  const topRisks = findings
    .filter((f) => f.severity !== "info")
    .slice(0, 3)
    .map((f) => ({ title: f.title, impact: f.impact }));

  return {
    scan: item,
    explanation: explanationFor(item),
    topRisks,
    surfaces: surfacesFor(item),
    findings,
  };
}

// ─── Live-view SSE synthesis (offline theater) ───────────────────────────────
//
// The theater's offline stream used to replay ONE hard-coded reel (fabrikam) for
// every scan, so a row for salud.gob.mx played fabrikam's findings. We synthesize
// the event sequence FROM the row instead, so the live feed matches both the row
// and the report (both derive findings from `findingsFor`). The hero keeps its
// hand-authored reel; unknown ids (e.g. a fresh `/scan` submit with no backend)
// fall back to it so the cinematic demo still plays.

/** The embedded Finding fields a `finding` event carries (06-data-model §6). */
function findingEventPayload(f: Finding): Record<string, unknown> {
  return {
    id: f.id,
    source: f.source,
    tool: f.tool,
    category: f.category,
    title: f.title,
    confidence: f.confidence,
    cvss: f.cvss,
    description: f.description,
    evidence: f.evidence,
    affectedUrl: f.affectedUrl,
    endpoint: f.endpoint,
    param: f.param,
    impact: f.impact,
    remediation: f.remediation,
    references: f.references,
  };
}

/** Synthesize a coherent SSE run from a single history row. */
function synthEventsFor(item: ScanHistoryItem): ScanEvent[] {
  const events: ScanEvent[] = [];
  let seq = 0;
  const t0 = Date.now();
  // Running rows hold at their current progress; nothing emitted exceeds it.
  const maxProgress =
    item.status === "running"
      ? Math.max(0, Math.min(95, item.progress ?? 50))
      : 100;
  const prog = (p: number) => Math.min(p, maxProgress);
  const push = (
    e: Omit<ScanEvent, "scan_id" | "seq" | "ts"> & { progress?: number | null }
  ) => {
    seq += 1;
    events.push({
      scan_id: item.scanId,
      seq,
      ts: new Date(t0 + seq * 900).toISOString(),
      ...e,
    });
  };

  const host = item.host;
  const hasAgentic =
    item.agenticStatus === "tested" ||
    item.agenticStatus === "detected_not_tested";

  // Queued: not started — the seed shows "en cola"; the stream just holds open.
  if (item.status === "queued") {
    push({
      type: "phase",
      message: `En cola — ${host} esperando un worker`,
      progress: 0,
      payload: {},
    });
    return events;
  }

  // ── Lead-in (every run) ──
  push({
    type: "phase",
    message: `Iniciando escaneo de ${host}`,
    progress: prog(3),
    payload: {},
  });
  push({
    type: "agent_status",
    agent: "owasp",
    message: "OWASP Scanner en línea",
    payload: {},
  });
  if (hasAgentic) {
    push({
      type: "agent_status",
      agent: "agentic",
      message: "Agentic Surface Auditor en línea",
      payload: {},
    });
  }
  push({
    type: "phase",
    message: "Detectando tecnologías…",
    progress: prog(12),
    payload: {},
  });
  push({
    type: "tool_start",
    agent: "owasp",
    tool: "nuclei",
    message: "nuclei: plantillas de exposición",
    payload: {},
  });
  push({
    type: "tool_start",
    agent: "owasp",
    tool: "testssl",
    message: "testssl: análisis de TLS",
    payload: {},
  });

  // ── Failed run → stop early with the row's error (terminal) ──
  if (item.status === "failed") {
    push({
      type: "phase",
      message: "Estableciendo conexión con el objetivo…",
      progress: prog(18),
      payload: {},
    });
    push({
      type: "tool_end",
      agent: "owasp",
      tool: "testssl",
      message: "testssl: la conexión falló",
      severity: "high",
      payload: { status: "failed" },
    });
    push({
      type: "error",
      message: item.error ?? "El escaneo no pudo completarse.",
      payload: {},
    });
    return events;
  }

  // ── Findings drop in (host-correct, same set as the report), split by lane ──
  const findings = findingsFor(item);
  const owaspFindings = findings.filter((f) => f.source !== "agentic");
  const agenticFindings = findings.filter((f) => f.source === "agentic");
  push({
    type: "tool_start",
    agent: "owasp",
    tool: "zap",
    message: "zap: escaneo pasivo",
    payload: {},
  });
  owaspFindings.forEach((f, i) => {
    push({
      type: "phase",
      message: `Analizando ${host}…`,
      progress: prog(20 + Math.round(((i + 1) / owaspFindings.length) * 45)),
      payload: {},
    });
    push({
      type: "tool_end",
      agent: "owasp",
      tool: f.tool,
      message: `${f.tool}: ${f.title}`,
      severity: f.severity,
      payload: { status: "ok" },
    });
    push({
      type: "finding",
      agent: "owasp",
      severity: f.severity,
      message: f.title,
      payload: findingEventPayload(f),
    });
  });
  if (typeof item.webScore === "number") {
    push({
      type: "score",
      agent: "owasp",
      message: "Puntaje web parcial",
      payload: { web_score: item.webScore },
    });
  }

  // ── Agentic lane ──
  if (hasAgentic) {
    const tested = item.agenticStatus === "tested";
    const running = item.status === "running";
    push({
      type: "phase",
      message: "Sondeando la superficie agéntica…",
      progress: prog(72),
      payload: {},
    });
    push({
      type: "agent_status",
      agent: "agentic",
      message: `Chatbot detectado en ${host}/asistente`,
      payload: {},
    });
    push({
      type: "tool_start",
      agent: "agentic",
      tool: "promptfoo",
      message: "promptfoo: sondas de inyección de prompt",
      payload: {},
    });
    // A running scan is still probing — leave the probe in flight (no tool_end /
    // findings / score until it finishes). Terminal scans complete the lane.
    if (!running) {
      push({
        type: "tool_end",
        agent: "agentic",
        tool: "promptfoo",
        message: tested
          ? "promptfoo: sondas completadas"
          : "promptfoo: superficie detectada, sin auditar",
        severity: tested ? "medium" : "info",
        payload: { status: tested ? "ok" : "timeout" },
      });
      agenticFindings.forEach((f) => {
        push({
          type: "finding",
          agent: "agentic",
          severity: f.severity,
          message: f.title,
          payload: findingEventPayload(f),
        });
      });
      if (typeof item.agenticScore === "number") {
        push({
          type: "score",
          agent: "agentic",
          message: "Puntaje agéntico parcial",
          payload: { agentic_score: item.agenticScore },
        });
      }
    }
  }

  // ── Running → hold here (no terminal); the seed carries the in-flight phase ──
  if (item.status === "running") {
    push({
      type: "phase",
      message: item.currentPhase ?? "Escaneando…",
      progress: prog(maxProgress),
      payload: {},
    });
    return events;
  }

  // ── Terminal wrap-up (done | partial | cancelled) ──
  const finalScore: Record<string, number> = {};
  if (typeof item.webScore === "number") finalScore.web_score = item.webScore;
  if (typeof item.agenticScore === "number")
    finalScore.agentic_score = item.agenticScore;
  push({
    type: "score",
    message: "Puntajes finales",
    payload: finalScore,
  });
  push({
    type: "phase",
    message: "Consolidando resultados…",
    progress: 92,
    payload: {},
  });
  push({
    type: "phase",
    message: "Generando reporte…",
    progress: 98,
    payload: {},
  });
  if (item.status === "cancelled") {
    push({
      type: "done",
      message: "Escaneo cancelado",
      progress: 100,
      payload: { outcome: "cancelled" },
    });
  } else {
    // `outcome` only carries success|cancelled; partial coverage rides in the
    // message so the live wording matches the report's "cobertura parcial".
    const gradeSuffix = item.overallGrade ? ` — grado ${item.overallGrade}` : "";
    push({
      type: "done",
      message:
        item.status === "partial"
          ? `Escaneo completo (cobertura parcial)${gradeSuffix}`
          : `Escaneo completo${gradeSuffix}`,
      progress: 100,
      payload: { outcome: "success" },
    });
  }
  return events;
}

/**
 * The demo SSE event sequence for an id (offline theater). Hero → the polished
 * hand-authored reel; any history row → events synthesized from its own data;
 * unknown id → the reel (so a fresh `/scan` submit still plays a full run).
 */
export function buildScanEventsFor(id: string): ScanEvent[] {
  if (id === HERO_SCAN_ID) return scanEventsFixture;
  const item = HISTORY_BY_ID.get(id);
  if (!item) return scanEventsFixture;
  return synthEventsFor(item);
}
