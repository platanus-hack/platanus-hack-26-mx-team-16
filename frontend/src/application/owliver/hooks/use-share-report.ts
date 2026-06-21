/**
 * useShareReport — screen hook for the report Share action (§F7). POSTs to the
 * same-origin BFF `/api/owliver/scans/{id}/share` (which forwards to backend
 * `POST /v1/scans/{id}/share` with cookie + X-Api-Key, fixture fallback), parses
 * the `{ token }` envelope, builds the absolute `/r/{token}` link and copies it
 * to the clipboard. State is exposed for inline feedback (no toast dep yet).
 */
"use client";

import * as React from "react";

import { shareResponseSchema } from "@/src/application/owliver/schemas/api";
import {
  firstErrorMessage,
  isErrorEnvelope,
  parseData,
} from "@/src/application/owliver/lib/envelope";

type ShareState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; url: string }
  | { status: "error"; message: string };

export function useShareReport(scanId: string) {
  const [state, setState] = React.useState<ShareState>({ status: "idle" });

  const share = React.useCallback(async () => {
    setState({ status: "loading" });
    try {
      const res = await fetch(`/api/owliver/scans/${scanId}/share`, {
        method: "POST",
      });
      const body = await res.json();

      if (!res.ok || isErrorEnvelope(body)) {
        setState({
          status: "error",
          message:
            firstErrorMessage(body) ?? "No se pudo generar el enlace público.",
        });
        return;
      }

      const { token } = parseData(shareResponseSchema, body);
      const url = `${window.location.origin}/r/${token}`;
      try {
        await navigator.clipboard.writeText(url);
      } catch {
        // Clipboard may be unavailable; the URL is still surfaced in state.
      }
      setState({ status: "done", url });
    } catch {
      setState({ status: "error", message: "Error de red al compartir." });
    }
  }, [scanId]);

  return { state, share };
}
