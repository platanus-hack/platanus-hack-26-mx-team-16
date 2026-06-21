/**
 * Theater store (zustand) — the live-view state machine for the Live Pentest
 * Theater (§F6). It is a pure reducer over `ScanEvent`s: `useScanStream` feeds
 * events in (replay then tail), the theater UI subscribes to slices.
 *
 * Load-bearing invariant: **replay is idempotent**. On reload the backend
 * repaints every event from Postgres; the store discards any `event.seq <=
 * lastSeq` so a replay never double-applies. `done`/`error` mark the run terminal.
 *
 * The store holds NO transport — it never opens a connection. That keeps it
 * trivially unit-testable with synthetic events (plan §9).
 */
import { create } from "zustand";

import type { FindingEvidence, Severity } from "../schemas/api";
import type {
  AgentLaneId,
  DoneEventPayload,
  FindingEventPayload,
  ScanEvent,
  ScoreEventPayload,
  ToolEndPayload,
} from "../schemas/sse";

export type ToolRunState = "idle" | "running" | "ok" | "failed";

export type LaneToolState = {
  tool: string;
  state: ToolRunState;
  message?: string;
};

export type AgentLaneState = {
  id: AgentLaneId;
  /** Latest `agent_status` message for the lane. */
  status: string;
  /** Tool chips keyed by tool name (insertion order preserved). */
  tools: Record<string, LaneToolState>;
  toolOrder: string[];
};

export type LiveFinding = {
  /** Stable key — event seq guarantees uniqueness even without an id. */
  key: string;
  seq: number;
  severity: Severity;
  source?: "owasp" | "agentic";
  tool?: string;
  category?: string;
  title: string;
  confidence?: "alta" | "media" | "baja";
  cvss?: number | null;
  description?: string;
  evidence?: FindingEvidence;
  affectedUrl?: string | null;
  endpoint?: string | null;
  param?: string | null;
  impact?: string;
  remediation?: string;
  references?: string[];
};

export type TheaterRunStatus =
  | "idle"
  | "running"
  | "done"
  | "cancelled"
  | "error";

export type TheaterState = {
  scanId: string | null;
  /** Highest applied seq — the replay cursor + idempotency guard. */
  lastSeq: number;
  runStatus: TheaterRunStatus;
  progress: number;
  currentPhase: string | null;
  webScore: number | null;
  agenticScore: number | null;
  lanes: Record<AgentLaneId, AgentLaneState>;
  findings: LiveFinding[];
  /** Monospace terminal log (every event, newest last). */
  log: { seq: number; ts: string; type: string; message: string }[];
  /** Terminal `done`/`error` message, when finished. */
  terminalMessage: string | null;

  // actions
  init: (scanId: string, sinceSeq?: number) => void;
  apply: (event: ScanEvent) => void;
  applyMany: (events: ScanEvent[]) => void;
  reset: () => void;
};

function emptyLane(id: AgentLaneId): AgentLaneState {
  return { id, status: "", tools: {}, toolOrder: [] };
}

function initialLanes(): Record<AgentLaneId, AgentLaneState> {
  return { owasp: emptyLane("owasp"), agentic: emptyLane("agentic") };
}

function laneFromAgent(agent: string | null | undefined): AgentLaneId {
  return agent === "agentic" ? "agentic" : "owasp";
}

const INITIAL: Omit<TheaterState, "init" | "apply" | "applyMany" | "reset"> = {
  scanId: null,
  lastSeq: 0,
  runStatus: "idle",
  progress: 0,
  currentPhase: null,
  webScore: null,
  agenticScore: null,
  lanes: initialLanes(),
  findings: [],
  log: [],
  terminalMessage: null,
};

export const useTheaterStore = create<TheaterState>((set, get) => ({
  ...INITIAL,

  init: (scanId, sinceSeq = 0) =>
    set({
      ...INITIAL,
      lanes: initialLanes(),
      findings: [],
      log: [],
      scanId,
      lastSeq: sinceSeq,
      runStatus: "running",
    }),

  applyMany: (events) => {
    for (const e of events) get().apply(e);
  },

  apply: (event) =>
    set((state) => {
      // Idempotent replay: never re-apply an event we've already seen.
      if (event.seq <= state.lastSeq) return state;

      const next: Partial<TheaterState> = {
        lastSeq: event.seq,
        log: [
          ...state.log,
          {
            seq: event.seq,
            ts: event.ts,
            type: event.type,
            message: event.message,
          },
        ].slice(-300), // bound the log buffer
      };

      if (typeof event.progress === "number") {
        next.progress = Math.max(0, Math.min(100, event.progress));
      }

      switch (event.type) {
        case "phase":
          next.currentPhase = event.message;
          break;

        case "agent_status": {
          const laneId = laneFromAgent(event.agent);
          next.lanes = {
            ...state.lanes,
            [laneId]: { ...state.lanes[laneId], status: event.message },
          };
          break;
        }

        case "tool_start": {
          const laneId = laneFromAgent(event.agent);
          const tool = event.tool ?? "tool";
          const lane = state.lanes[laneId];
          next.lanes = {
            ...state.lanes,
            [laneId]: {
              ...lane,
              tools: {
                ...lane.tools,
                [tool]: { tool, state: "running", message: event.message },
              },
              toolOrder: lane.toolOrder.includes(tool)
                ? lane.toolOrder
                : [...lane.toolOrder, tool],
            },
          };
          break;
        }

        case "tool_end": {
          const laneId = laneFromAgent(event.agent);
          const tool = event.tool ?? "tool";
          const lane = state.lanes[laneId];
          const status = (event.payload as ToolEndPayload)?.status;
          const runState: ToolRunState =
            status === "failed" || status === "timeout" ? "failed" : "ok";
          next.lanes = {
            ...state.lanes,
            [laneId]: {
              ...lane,
              tools: {
                ...lane.tools,
                [tool]: { tool, state: runState, message: event.message },
              },
              toolOrder: lane.toolOrder.includes(tool)
                ? lane.toolOrder
                : [...lane.toolOrder, tool],
            },
          };
          break;
        }

        case "finding": {
          const p = event.payload as FindingEventPayload;
          const finding: LiveFinding = {
            key: p.id ?? `finding-${event.seq}`,
            seq: event.seq,
            severity: (event.severity ?? "info") as Severity,
            source: p.source,
            tool: p.tool,
            category: p.category,
            title: p.title ?? event.message,
            confidence: p.confidence,
            cvss: p.cvss,
            description: p.description,
            evidence: p.evidence as FindingEvidence | undefined,
            affectedUrl: p.affectedUrl ?? p.affected_url,
            endpoint: p.endpoint,
            param: p.param,
            impact: p.impact,
            remediation: p.remediation,
            references: p.references,
          };
          next.findings = [...state.findings, finding];
          break;
        }

        case "score": {
          const p = event.payload as ScoreEventPayload;
          if (typeof p.web_score === "number") next.webScore = p.web_score;
          if (typeof p.agentic_score === "number")
            next.agenticScore = p.agentic_score;
          break;
        }

        case "done": {
          const outcome = (event.payload as DoneEventPayload)?.outcome;
          next.runStatus = outcome === "cancelled" ? "cancelled" : "done";
          next.progress = 100;
          next.terminalMessage = event.message;
          break;
        }

        case "error":
          next.runStatus = "error";
          next.terminalMessage = event.message;
          break;
      }

      return { ...state, ...next };
    }),

  reset: () =>
    set({ ...INITIAL, lanes: initialLanes(), findings: [], log: [] }),
}));

/** Selector: is the run in a terminal state (done/cancelled/error)? */
export function isTerminal(status: TheaterRunStatus): boolean {
  return status === "done" || status === "cancelled" || status === "error";
}
