/**
 * Owliver API DTO schemas (zod) — the camelCase envelope the BFF returns.
 *
 * These mirror the FROZEN backend contracts (06-data-model `finding.py`,
 * `events.py`; 07-scoring; 12-api). The backend presenters convert snake_case →
 * camelCase, so every field here is camelCase. The frontend NEVER computes a
 * score, grade or `dedupeKey` — it renders the server values as-is.
 *
 * Used to validate fixtures (and, when wired, real BFF responses) and to derive
 * the TypeScript types every screen imports.
 */
import { z } from "zod";

// ─── Primitive enums (mirror the backend Literals verbatim) ───

export const gradeSchema = z.enum(["A", "B", "C", "D", "E", "F"]);
export type Grade = z.infer<typeof gradeSchema>;

export const severitySchema = z.enum([
  "critical",
  "high",
  "medium",
  "low",
  "info",
]);
export type Severity = z.infer<typeof severitySchema>;

export const confidenceSchema = z.enum(["alta", "media", "baja"]);
export type Confidence = z.infer<typeof confidenceSchema>;

/** A finding's origin dimension: OWASP (web) vs the agentic surface. */
export const sourceSchema = z.enum(["owasp", "agentic"]);
export type Source = z.infer<typeof sourceSchema>;

/**
 * Agentic surface coverage state (07-scoring / finding.py).
 * - `no_surface`          — no chatbot/IA widget detected.
 * - `detected_not_tested` — IA found but not probed → badge "IA detectada, sin auditar".
 * - `tested`              — probed; agentic score is authoritative.
 */
export const agenticStatusSchema = z.enum([
  "no_surface",
  "detected_not_tested",
  "tested",
]);
export type AgenticStatus = z.infer<typeof agenticStatusSchema>;

/** Scan lifecycle status (06-data-model `scans.status`). */
export const scanStatusSchema = z.enum([
  "queued",
  "running",
  "done",
  "partial",
  "failed",
  "cancelled",
]);
export type ScanStatus = z.infer<typeof scanStatusSchema>;

/** Attack level (02-attack-levels). `basico` is passive/anonymous. */
export const scanLevelSchema = z.enum(["basico", "intermedio", "avanzado"]);
export type ScanLevel = z.infer<typeof scanLevelSchema>;

/** Public board vs private (active/owned) scan visibility. */
export const visibilitySchema = z.enum(["public", "private"]);
export type Visibility = z.infer<typeof visibilitySchema>;

/** Per-tool coverage outcome (drives the "cobertura parcial" label). */
export const toolStatusSchema = z.enum([
  "queued",
  "running",
  "done",
  "ok",
  "failed",
  "timeout",
  "skipped",
]);
export type ToolStatus = z.infer<typeof toolStatusSchema>;

// ─── Finding (06-data-model `finding.py`, camelCased) ───

export const findingEvidenceSchema = z
  .object({
    /** Raw request/exploit payload — REDACTED in /r/{token}. */
    payload: z.string().optional(),
    request: z.string().optional(),
    response: z.string().optional(),
    /** Relative screenshot URL (never base64). */
    screenshot: z.string().optional(),
    /** Star agentic finding: the leaked canary token (incontestable proof). */
    canary: z.string().optional(),
    verdict: z.string().optional(),
    reason: z.string().optional(),
  })
  .catchall(z.unknown());
export type FindingEvidence = z.infer<typeof findingEvidenceSchema>;

export const findingSchema = z.object({
  /** Stable id for keys/accordion (uuid). */
  id: z.string(),
  source: sourceSchema,
  tool: z.string(),
  /** OWASP A01..A10 or OWASP-LLM LLM01..LLM10 (assigned server-side). */
  category: z.string(),
  title: z.string(),
  severity: severitySchema,
  cvss: z.number().nullable().optional(),
  confidence: confidenceSchema,
  description: z.string(),
  evidence: findingEvidenceSchema.default({}),
  affectedUrl: z.string().nullable().optional(),
  endpoint: z.string().nullable().optional(),
  param: z.string().nullable().optional(),
  impact: z.string(),
  remediation: z.string(),
  references: z.array(z.string()).default([]),
});
export type Finding = z.infer<typeof findingSchema>;

/**
 * Redacted finding shape for the public report (/r/{token}). Same headers as a
 * Finding but the raw exploit `evidence` is stripped server-side; the UI shows a
 * lock state. `redacted=true` marks that a payload was withheld.
 */
export const redactedFindingSchema = findingSchema
  .omit({ evidence: true })
  .extend({
    redacted: z.boolean().default(true),
  });
export type RedactedFinding = z.infer<typeof redactedFindingSchema>;

// ─── Agentic surface inventory (finding.py `AgenticResult`) ───

export const agenticSurfaceSchema = z.object({
  type: z.string(), // chatbot | prompt_input | search_ai
  vendor: z.string().nullable().optional(), // Intercom, Drift… or null (generic)
  locationUrl: z.string(),
  inferredModel: z.string().nullable().optional(), // null = "modelo no expuesto"
  agenticStatus: agenticStatusSchema,
});
export type AgenticSurface = z.infer<typeof agenticSurfaceSchema>;

// ─── Scan (GET /scans/{id}) ───

export const scanSchema = z.object({
  /** PK surfaced as `scanId` (UUIDv4, non-enumerable) — matches the backend
   * `ScanDetailPresenter`/`POST /scans` contract across the app. */
  scanId: z.string(),
  siteId: z.string(),
  host: z.string(),
  level: scanLevelSchema,
  visibility: visibilitySchema,
  status: scanStatusSchema,
  /** 0..100 live progress. */
  progress: z.number().min(0).max(100).default(0),
  /** Human phase label, e.g. "Sondeando chatbot…". */
  currentPhase: z.string().nullable().optional(),
  /** 0..100 sub-scores (server-computed; null until done). */
  webScore: z.number().nullable().optional(),
  agenticScore: z.number().nullable().optional(),
  overallScore: z.number().nullable().optional(),
  /** Authoritative overall grade (null until done). */
  overallGrade: gradeSchema.nullable().optional(),
  /** Display-only per-dimension grades (07-scoring §5.1). */
  webGrade: gradeSchema.nullable().optional(),
  agenticGrade: gradeSchema.nullable().optional(),
  /** Raw web penalty (unclamped — leaderboard tiebreak). */
  penaltyRaw: z.number().nullable().optional(),
  /** Null on a freshly-queued scan (the agentic phase hasn't run yet). */
  agenticStatus: agenticStatusSchema.nullable().optional(),
  /** `{ nuclei: 'done', zap: 'running' }`. `null` on a freshly-queued scan. */
  toolsStatus: z
    .record(z.string(), toolStatusSchema)
    .nullish()
    .transform((v) => v ?? {}),
  /** Per-tool coverage `[{ tool, status }]` (list; `null` until tools run). */
  coverage: z
    .array(z.object({ tool: z.string(), status: toolStatusSchema }))
    .nullish()
    .transform((v) => v ?? []),
  /** True when status=partial → grade capped at C. */
  partialCoverage: z.boolean().default(false),
  error: z.string().nullable().optional(),
  startedAt: z.string().nullable().optional(),
  finishedAt: z.string().nullable().optional(),
  createdAt: z.string().nullable().optional(),
  updatedAt: z.string().nullable().optional(),
});
export type Scan = z.infer<typeof scanSchema>;

// ─── Report (executive layer + findings; 09-reporting) ───

export const reportSchema = z.object({
  scan: scanSchema,
  /** Opus plain-language synthesis ("Owliver te explica"). */
  explanation: z.string(),
  /** Top 3 prioritized risks with business impact. */
  topRisks: z
    .array(z.object({ title: z.string(), impact: z.string() }))
    .default([]),
  surfaces: z.array(agenticSurfaceSchema).default([]),
  findings: z.array(findingSchema).default([]),
});
export type Report = z.infer<typeof reportSchema>;

/** Public (redacted) report — what /r/{token} renders. */
export const publicReportSchema = reportSchema
  .omit({ findings: true })
  .extend({
    findings: z.array(redactedFindingSchema).default([]),
    /** Site display name + grade for the share/OG card. */
    departmentName: z.string().nullable().optional(),
  });
export type PublicReport = z.infer<typeof publicReportSchema>;

// ─── Ranking row (GET /ranking?country=mx — worst-first) ───

export const trendSchema = z.enum(["up", "down", "flat"]);
export type Trend = z.infer<typeof trendSchema>;

export const rankingRowSchema = z.object({
  /** site id — click target → /sites/{id}. */
  siteId: z.string(),
  rank: z.number(),
  host: z.string(),
  /** Organization / site display name. */
  departmentName: z.string(),
  faviconUrl: z.string().nullable().optional(),
  country: z.string().default("mx"),
  overallGrade: gradeSchema,
  webScore: z.number().nullable().optional(),
  agenticScore: z.number().nullable().optional(),
  webGrade: gradeSchema.nullable().optional(),
  agenticGrade: gradeSchema.nullable().optional(),
  /** Unclamped web penalty — the worst-first tiebreak, shown on the row. */
  penaltyRaw: z.number(),
  agenticStatus: agenticStatusSchema,
  partialCoverage: z.boolean().default(false),
  /** ▲▼ vs previous scan (display only). */
  trend: trendSchema.nullable().optional(),
  /** One-liner "why" surfaced on hover (top finding). */
  topFinding: z.string().nullable().optional(),
  lastScanAt: z.string().nullable().optional(),
});
export type RankingRow = z.infer<typeof rankingRowSchema>;

// ─── Site history (GET /sites/{id}) ───

export const scanHistoryEntrySchema = z.object({
  scanId: z.string(),
  overallGrade: gradeSchema,
  webScore: z.number().nullable().optional(),
  agenticScore: z.number().nullable().optional(),
  scannedAt: z.string(),
});
export type ScanHistoryEntry = z.infer<typeof scanHistoryEntrySchema>;

export const siteSchema = z.object({
  id: z.string(),
  host: z.string(),
  departmentName: z.string().nullable().optional(),
  faviconUrl: z.string().nullable().optional(),
  /** Most recent scan summary. */
  latestScan: scanSchema,
  /** Chronological grade timeline (oldest → newest). */
  history: z.array(scanHistoryEntrySchema).default([]),
  surfaces: z.array(agenticSurfaceSchema).default([]),
});
export type Site = z.infer<typeof siteSchema>;

// ─── Watchlist (GET /watchlist — `id` is the watchlist-row uuid) ───

export const watchlistRowSchema = z.object({
  /** watchlist-row uuid — used for PATCH/DELETE (NEVER siteId). */
  id: z.string(),
  siteId: z.string(),
  host: z.string(),
  departmentName: z.string().nullable().optional(),
  overallGrade: gradeSchema.nullable().optional(),
  webGrade: gradeSchema.nullable().optional(),
  agenticGrade: gradeSchema.nullable().optional(),
  agenticStatus: agenticStatusSchema.default("no_surface"),
  monitor: z.boolean().default(false),
  lastScanAt: z.string().nullable().optional(),
});
export type WatchlistRow = z.infer<typeof watchlistRowSchema>;

// ─── Account alert prefs (GET/PUT /me/alerts) ───

export const alertPrefsSchema = z.object({
  emailEnabled: z.boolean().default(true),
  slackWebhookUrl: z.string().nullable().optional(),
});
export type AlertPrefs = z.infer<typeof alertPrefsSchema>;

// ─── POST /scans response ───

export const createScanResponseSchema = z.object({
  scanId: z.string(),
});
export type CreateScanResponse = z.infer<typeof createScanResponseSchema>;

// ─── POST /scans/{id}/share response ───

export const shareResponseSchema = z.object({
  token: z.string(),
  expiresAt: z.string().nullable().optional(),
});
export type ShareResponse = z.infer<typeof shareResponseSchema>;
