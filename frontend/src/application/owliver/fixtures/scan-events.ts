/**
 * Scan-events stream fixture (§F6, 10-realtime-live-view) — a monotonic `seq`
 * sequence that drives the theater store the same way a live SSE stream would.
 * Used for: the Plan-B "replay cinematográfico" (§F14-3), the theater in offline
 * mode, and store unit tests. Feed it through `useTheaterStore.applyMany` or
 * replay it on a timer.
 */
import type { ScanEvent } from "../schemas/sse";
import { HERO_SCAN_ID } from "./scan";

let seq = 0;
const t0 = Date.now();
function ev(e: Omit<ScanEvent, "scan_id" | "seq" | "ts">): ScanEvent {
  seq += 1;
  return {
    scan_id: HERO_SCAN_ID,
    seq,
    ts: new Date(t0 + seq * 900).toISOString(),
    ...e,
  };
}

/**
 * ~30 events: phases, both lanes' tools igniting/finishing, findings dropping
 * (incl. the critical star finding), score updates, and a terminal `done`.
 */
export const scanEventsFixture: ScanEvent[] = [
  ev({ type: "phase", message: "Iniciando escaneo de fabrikam.com", progress: 2, payload: {} }),
  ev({ type: "agent_status", agent: "owasp", message: "OWASP Scanner en línea", payload: {} }),
  ev({ type: "agent_status", agent: "agentic", message: "Agentic Surface Auditor en línea", payload: {} }),
  ev({ type: "phase", message: "Detectando tecnologías…", progress: 10, payload: {} }),
  ev({ type: "tool_start", agent: "owasp", tool: "nuclei", message: "nuclei: plantillas de exposición", payload: {} }),
  ev({ type: "tool_start", agent: "owasp", tool: "testssl", message: "testssl: análisis de TLS", payload: {} }),
  ev({ type: "phase", message: "Analizando configuración TLS…", progress: 22, payload: {} }),
  ev({ type: "tool_end", agent: "owasp", tool: "testssl", message: "testssl: TLS 1.0/1.1 habilitado", severity: "high", payload: { status: "ok" } }),
  ev({ type: "finding", agent: "owasp", severity: "high", message: "Suites de cifrado débiles (TLS 1.0/1.1)", payload: { id: "f-tls-weak", source: "owasp", category: "A02", title: "Suites de cifrado débiles (TLS 1.0/1.1)" } }),
  ev({ type: "score", agent: "owasp", message: "Score web parcial", payload: { web_score: 64 } }),
  ev({ type: "tool_start", agent: "owasp", tool: "zap", message: "zap: escaneo pasivo", payload: {} }),
  ev({ type: "agent_status", agent: "agentic", message: "Detectando superficie agéntica…", payload: {} }),
  ev({ type: "phase", message: "Sondeando chatbot…", progress: 40, payload: {} }),
  ev({ type: "tool_end", agent: "owasp", tool: "nuclei", message: "nuclei: cabeceras ausentes", severity: "medium", payload: { status: "ok" } }),
  ev({ type: "finding", agent: "owasp", severity: "medium", message: "Cabeceras de seguridad ausentes", payload: { id: "f-headers", source: "owasp", category: "A05", title: "Cabeceras de seguridad ausentes (CSP, HSTS)" } }),
  ev({ type: "agent_status", agent: "agentic", message: "Chatbot detectado: Intercom (gpt-4o-mini inferido)", payload: {} }),
  ev({ type: "tool_start", agent: "agentic", tool: "promptfoo", message: "promptfoo: sondas de inyección", payload: {} }),
  ev({ type: "phase", message: "Lanzando inyecciones de prompt…", progress: 58, payload: {} }),
  ev({ type: "tool_start", agent: "agentic", tool: "garak", message: "garak: jailbreaks", payload: {} }),
  ev({ type: "tool_end", agent: "owasp", tool: "zap", message: "zap: cookie sin Secure", severity: "low", payload: { status: "ok" } }),
  ev({ type: "finding", agent: "owasp", severity: "low", message: "Cookie de sesión sin Secure", payload: { id: "f-cookie", source: "owasp", category: "A05", title: "Cookie de sesión sin atributo Secure" } }),
  ev({ type: "phase", message: "Verificando canario sembrado…", progress: 72, payload: {} }),
  ev({ type: "tool_end", agent: "agentic", tool: "promptfoo", message: "promptfoo: ¡canario filtrado!", severity: "critical", payload: { status: "ok" } }),
  ev({ type: "finding", agent: "agentic", severity: "critical", message: "Fuga de system-prompt del asistente (canary filtrado)", payload: { id: "f-agentic-leak", source: "agentic", category: "LLM01", title: "Fuga de system-prompt del asistente de compras" } }),
  ev({ type: "score", agent: "agentic", message: "Score agéntico parcial", payload: { agentic_score: 24 } }),
  ev({ type: "tool_end", agent: "agentic", tool: "garak", message: "garak: jailbreak parcial", severity: "high", payload: { status: "ok" } }),
  ev({ type: "phase", message: "Consolidando resultados…", progress: 90, payload: {} }),
  ev({ type: "score", message: "Scores finales", payload: { web_score: 72, agentic_score: 24 } }),
  ev({ type: "phase", message: "Generando reporte…", progress: 98, payload: {} }),
  ev({ type: "done", message: "Escaneo completo — grado E", progress: 100, payload: { outcome: "success" } }),
];

/** Raw SSE wire frames (event:/id:/data:) for testing `subscribeSSE` parsing. */
export function scanEventsAsSSEWire(): string {
  return (
    scanEventsFixture
      .map(
        (e) =>
          `event: ${e.type}\nid: ${e.seq}\ndata: ${JSON.stringify(e)}\n`
      )
      .join("\n") + "\n"
  );
}
