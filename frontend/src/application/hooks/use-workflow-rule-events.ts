"use client";

import { useEffect, useRef } from "react";
import { subscribeSSE } from "@/src/infrastructure/http/sse";

export type WorkflowRuleEventType =
  | "COMPILATION_STARTED"
  | "COMPILATION_COMPLETED"
  | "COMPILATION_FAILED"
  | "COMPILATION_INVALIDATED"
  | "RULE_RESULT_COMPLETED";

const KNOWN_TYPES: ReadonlySet<WorkflowRuleEventType> = new Set<WorkflowRuleEventType>([
  "COMPILATION_STARTED",
  "COMPILATION_COMPLETED",
  "COMPILATION_FAILED",
  "COMPILATION_INVALIDATED",
  "RULE_RESULT_COMPLETED",
]);

export interface WorkflowRuleEvent {
  type: WorkflowRuleEventType;
  ruleId: string;
  workflowId: string;
  compilationId?: string | null;
  version?: number | null;
  error?: string | null;
  reason?: string | null;
}

interface RawEvent {
  type?: unknown;
  rule_id?: unknown;
  ruleId?: unknown;
  workflow_id?: unknown;
  workflowId?: unknown;
  compilation_id?: unknown;
  compilationId?: unknown;
  version?: unknown;
  error?: unknown;
  reason?: unknown;
}

function pickString(obj: RawEvent, ...keys: Array<keyof RawEvent>): string | null {
  for (const key of keys) {
    const value = obj[key];
    if (typeof value === "string" && value) return value;
  }
  return null;
}

function normalize(parsed: unknown): WorkflowRuleEvent | null {
  if (!parsed || typeof parsed !== "object") return null;
  const r = parsed as RawEvent;
  const type = typeof r.type === "string" ? (r.type as WorkflowRuleEventType) : null;
  if (!type || !KNOWN_TYPES.has(type)) return null;
  const ruleId = pickString(r, "rule_id", "ruleId");
  const workflowId = pickString(r, "workflow_id", "workflowId");
  if (!ruleId || !workflowId) return null;
  return {
    type,
    ruleId,
    workflowId,
    compilationId: pickString(r, "compilation_id", "compilationId"),
    version: typeof r.version === "number" ? r.version : null,
    error: pickString(r, "error"),
    reason: pickString(r, "reason"),
  };
}

export function useWorkflowRuleEvents(
  workflowId: string,
  onEvent: (event: WorkflowRuleEvent) => void,
): void {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!workflowId) return;
    const url = `/api/v1/workflows/${workflowId}/workflow-rules/events`;
    const close = subscribeSSE(url, {
      onEvent: (raw) => {
        if (!raw.data) return;
        let parsed: unknown;
        try {
          parsed = JSON.parse(raw.data);
        } catch {
          return;
        }
        const event = normalize(parsed);
        if (!event) return;
        handlerRef.current(event);
      },
    });
    return () => close();
  }, [workflowId]);
}
