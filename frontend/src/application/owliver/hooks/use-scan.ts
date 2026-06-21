/**
 * `useScan` — the initial Live Theater state (§F6): `GET /api/owliver/scans/{id}`
 * (status, progress, current_phase, tools_status, partial scores, visibility). The
 * live deltas afterwards come from `useScanStream` → theater store; this query
 * just seeds the header + handles the 404 (private scan, no permission) case.
 *
 * `useCancelScan` — `POST /api/owliver/scans/{id}/cancel`; the backend then emits
 * a terminal `done {outcome:'cancelled'}` on the stream, which the store applies.
 */
"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { firstErrorMessage } from "../lib/envelope";
import { parseData } from "../lib/envelope";
import { owliverKeys } from "./query-keys";
import { type Scan, scanSchema } from "../schemas/api";

export type ScanQueryError = { status: number; message: string };

async function fetchScan(id: string): Promise<Scan> {
  const res = await fetch(`/api/owliver/scans/${id}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const body = await res.json().catch(() => null);

  if (!res.ok) {
    const err: ScanQueryError = {
      status: res.status,
      message:
        firstErrorMessage(body) ??
        (res.status === 404
          ? "Escaneo no encontrado"
          : "No se pudo cargar el escaneo"),
    };
    throw err;
  }
  return parseData(scanSchema, body);
}

export function useScan(id: string, enabled = true) {
  return useQuery<Scan, ScanQueryError>({
    queryKey: owliverKeys.scan(id),
    queryFn: () => fetchScan(id),
    enabled: enabled && Boolean(id),
    // The theater header is seeded once; live state flows via SSE, not polling.
    staleTime: 30_000,
    retry: (count, err) => err.status !== 404 && count < 2,
  });
}

export function useCancelScan(id: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      const res = await fetch(`/api/owliver/scans/${id}/cancel`, {
        method: "POST",
        credentials: "same-origin",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          firstErrorMessage(body) ?? "No se pudo cancelar el escaneo"
        );
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: owliverKeys.scan(id) });
    },
  });
}
