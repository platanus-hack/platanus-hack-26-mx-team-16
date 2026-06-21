/**
 * Account alert-preferences hooks (§F11) — read + persist the email/Slack alert
 * config the watchlist manages. Backed by the BFF (`/api/owliver/me/alerts`),
 * which falls back to the fixture for GET so the panel renders offline.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { type DataEnvelope, parseData } from "../lib/envelope";
import { type AlertPrefs, alertPrefsSchema } from "../schemas/api";
import { owliverKeys } from "./query-keys";

async function getAlertPrefs(): Promise<AlertPrefs> {
  const res = await fetch("/api/owliver/me/alerts", {
    credentials: "same-origin",
  });
  if (!res.ok) throw new Error(`alerts ${res.status}`);
  const body = (await res.json()) as DataEnvelope<unknown>;
  return alertPrefsSchema.parse(body.data);
}

export function useAlertPrefs() {
  return useQuery({
    queryKey: owliverKeys.alertPrefs(),
    queryFn: getAlertPrefs,
  });
}

export function useUpdateAlertPrefs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: AlertPrefs) => {
      const res = await fetch("/api/owliver/me/alerts", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`alerts put ${res.status}`);
      return parseData(alertPrefsSchema, await res.json());
    },
    onSuccess: (data) => {
      qc.setQueryData(owliverKeys.alertPrefs(), data);
      qc.invalidateQueries({ queryKey: owliverKeys.alertPrefs() });
    },
  });
}
