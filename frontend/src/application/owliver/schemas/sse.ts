/**
 * Live-view SSE event schema — mirror of the FROZEN backend `events.py`
 * (06-data-model §6, 10-realtime-live-view). One `ScanEvent` per `scan_events`
 * row. `seq` is monotonic per scan and is the SINGLE source of order; the client
 * discards `seq <= lastSeq` on replay (idempotent replay-then-tail).
 *
 * `type` is the discriminant. `tool`/`severity`/`progress` are only present on
 * the relevant types. `done` carries `{ outcome }` in its payload
 * (`success` | `cancelled`). `done`/`error` are TERMINAL — they close the stream.
 */
import { z } from "zod";

import { severitySchema } from "./api";

export const scanEventTypeSchema = z.enum([
  "agent_status",
  "tool_start",
  "tool_end",
  "finding",
  "phase",
  "score",
  "done",
  "error",
]);
export type ScanEventType = z.infer<typeof scanEventTypeSchema>;

/** Terminal event types — emitting one closes the live stream. */
export const TERMINAL_EVENT_TYPES: ReadonlySet<ScanEventType> = new Set([
  "done",
  "error",
]);

/** Agent lane identifiers (05-agent-team — two Sonnet subagents). */
export const agentLaneSchema = z.enum(["owasp", "agentic"]);
export type AgentLaneId = z.infer<typeof agentLaneSchema>;

export const scanEventSchema = z.object({
  // The SSE wire mirrors the FROZEN backend `events.py` model verbatim (no
  // presenter on this path), so this field is snake_case `scan_id` — unlike the
  // camelCased REST DTOs. Consumers key off `seq`, never this id.
  scan_id: z.string(),
  /** monotonic per scan — single source of order. */
  seq: z.number(),
  ts: z.string(),
  type: scanEventTypeSchema,
  /** "owasp" | "agentic" on agent_status / tool_* events. */
  agent: z.string().nullable().optional(),
  /** tool name on tool_start / tool_end. */
  tool: z.string().nullable().optional(),
  severity: severitySchema.nullable().optional(),
  message: z.string(),
  /**
   * Type-dependent extras:
   * - finding   → the embedded Finding fields (category, title, source, …).
   * - score     → `{ web_score, agentic_score }` (snake — raw wire, no presenter).
   * - tool_end  → `{ status: 'ok'|'failed'|'timeout' }`.
   * - done      → `{ outcome: 'success'|'cancelled' }`.
   */
  payload: z.record(z.string(), z.unknown()).default({}),
  /** 0..100 on phase / score events. */
  progress: z.number().nullable().optional(),
});
export type ScanEvent = z.infer<typeof scanEventSchema>;

/** Narrowed payload accessors (the payload is intentionally loose). */
export type ScoreEventPayload = { web_score?: number; agentic_score?: number };
export type ToolEndPayload = { status?: "ok" | "failed" | "timeout" };
export type DoneEventPayload = { outcome?: "success" | "cancelled" };
export type FindingEventPayload = {
  id?: string;
  source?: "owasp" | "agentic";
  tool?: string;
  category?: string;
  title?: string;
  confidence?: "alta" | "media" | "baja";
  cvss?: number | null;
  description?: string;
  evidence?: Record<string, unknown>;
  affectedUrl?: string | null;
  affected_url?: string | null;
  endpoint?: string | null;
  param?: string | null;
  impact?: string;
  remediation?: string;
  references?: string[];
};
