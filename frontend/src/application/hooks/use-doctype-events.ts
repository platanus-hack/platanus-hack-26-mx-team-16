"use client";

import { useEffect, useRef } from "react";
import { subscribeSSE } from "@/src/infrastructure/http/sse";

export type DoctypeEventType =
  | "SAMPLE_TEXT_EXTRACTING"
  | "SAMPLE_TEXT_EXTRACTED"
  | "SAMPLE_TEXT_FAILED"
  | "FIELDS_SUGGESTING"
  | "FIELDS_SUGGESTED"
  | "FIELDS_SUGGESTION_FAILED";

export interface DocumentTypeEvent {
  type: DoctypeEventType;
  document_type_id: string;
  payload: Record<string, unknown>;
}

interface DoctypeEventCallbacks {
  onSampleTextExtracting?: () => void;
  onSampleTextExtracted?: () => void;
  onSampleTextFailed?: (error?: string) => void;
  onFieldsSuggested?: () => void;
  onFieldsSuggestionFailed?: (error?: string) => void;
}

const TERMINAL_EVENTS = new Set<DoctypeEventType>([
  "SAMPLE_TEXT_EXTRACTED",
  "SAMPLE_TEXT_FAILED",
  "FIELDS_SUGGESTED",
  "FIELDS_SUGGESTION_FAILED",
]);

/**
 * Abre un SSE stream contra /v1/document-types/{id}/events.
 * Cierra la conexión al recibir un evento terminal.
 * Reconecta cuando `triggerKey` cambia — permite escuchar ciclos sucesivos
 * (p. ej. una segunda extracción tras reemplazar el documento de ejemplo).
 */
export function useDoctypeEvents(
  doctypeId: string | undefined,
  callbacks: DoctypeEventCallbacks,
  triggerKey: unknown = 0
) {
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  useEffect(() => {
    if (!doctypeId) return;
    const controller = new AbortController();

    const cleanup = subscribeSSE(
      () => `/api/v1/document-types/${doctypeId}/events`,
      {
        signal: controller.signal,
        onEvent({ type, data }) {
          if (type === "ready" || type === "heartbeat") return;
          if (!data || data === "{}") return;
          let event: DocumentTypeEvent;
          try {
            event = JSON.parse(data) as DocumentTypeEvent;
          } catch {
            return;
          }
          const cb = callbacksRef.current;
          const error = event.payload.error as string | undefined;
          const handlerMap: Partial<Record<DoctypeEventType, () => void>> = {
            SAMPLE_TEXT_EXTRACTING: () => cb.onSampleTextExtracting?.(),
            SAMPLE_TEXT_EXTRACTED: () => cb.onSampleTextExtracted?.(),
            SAMPLE_TEXT_FAILED: () => cb.onSampleTextFailed?.(error),
            FIELDS_SUGGESTED: () => cb.onFieldsSuggested?.(),
            FIELDS_SUGGESTION_FAILED: () =>
              cb.onFieldsSuggestionFailed?.(error),
          };
          handlerMap[event.type]?.();
          if (TERMINAL_EVENTS.has(event.type)) controller.abort();
        },
      }
    );

    return () => {
      controller.abort();
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doctypeId, triggerKey]);
}
