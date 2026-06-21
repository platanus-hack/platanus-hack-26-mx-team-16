/**
 * useCreateScan (§F5) — POST a scan request through the BFF and resolve the
 * `scanId` so the form can redirect to `/scans/[id]` (the Live Theater).
 *
 * Client → same-origin `/api/owliver/scans` (BFF) → serverHttp `/v1/scans`.
 * NEVER fetches the backend directly (CLAUDE.md BFF rule).
 *
 * The mutation surfaces the API envelope verbatim on error so the form can map:
 *  - 422 → attestation/validation (inline)
 *  - 429 → rate-limited (Retry-After, inline)
 *  - 403 → forbidden (toast)
 * The backend is idempotent: a 200 with an existing `scanId` redirects too.
 */
import { useMutation } from "@tanstack/react-query";

import { createScanResponseSchema } from "@/src/application/owliver/schemas/api";
import type { ScanRequestBody } from "@/src/application/owliver/schemas/scan-form";

export type CreateScanError = {
  status: number;
  /** Retry-After seconds (429 only), if the backend sent one. */
  retryAfter: number | null;
  /** Raw error payload (envelope `{ errors }` or rate-limit `{ error }`). */
  body: unknown;
};

async function createScan(body: ScanRequestBody): Promise<{ scanId: string }> {
  const res = await fetch("/api/owliver/scans", {
    method: "POST",
    headers: { "content-type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let payload: unknown = null;
    try {
      payload = await res.json();
    } catch {
      payload = null;
    }
    const retryHeader = res.headers.get("retry-after");
    const err: CreateScanError = {
      status: res.status,
      retryAfter: retryHeader ? Number.parseInt(retryHeader, 10) : null,
      body: payload,
    };
    throw err;
  }

  const json = await res.json();
  // BFF returns the success envelope `{ data: { scanId } }`.
  const data = (json as { data?: unknown })?.data ?? json;
  return createScanResponseSchema.parse(data);
}

export function useCreateScan() {
  return useMutation<{ scanId: string }, CreateScanError, ScanRequestBody>({
    mutationFn: createScan,
  });
}
