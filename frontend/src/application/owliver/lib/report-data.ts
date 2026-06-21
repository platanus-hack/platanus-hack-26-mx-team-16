/**
 * Server-only report fetchers (§F7/§F8). RSC anonymous surfaces (the report and
 * the public `/r/{token}`) call these directly — they forward to the backend via
 * `backendGet` and fall back to the demo fixtures so the screens render without a
 * live backend. The `status` is preserved so the page can branch to 404/410.
 */
import "server-only";

import {
  publicReportSchema,
  reportSchema,
  type PublicReport,
  type Report,
} from "@/src/application/owliver/schemas/api";
import {
  publicReportFixture,
  reportFixture,
} from "@/src/application/owliver/fixtures";
import { parseData } from "@/src/application/owliver/lib/envelope";
import { backendGet } from "@/src/application/owliver/lib/bff";

/** Full in-app report. `null` → 404 (private/missing); fixture fallback offline. */
export async function fetchReport(scanId: string): Promise<Report | null> {
  const result = await backendGet(`/scans/${scanId}/report`);
  if (result.ok) {
    return parseData(reportSchema, result.data);
  }
  if (result.status === 404) {
    return null;
  }
  return reportFixture;
}

export type PublicReportResult =
  | { status: "ok"; report: PublicReport }
  | { status: "not_found" }
  | { status: "gone" };

/**
 * Public redacted report by share token. 404 → missing, 410 → expired/revoked,
 * 200 → redacted report. Any other backend failure (incl. offline) falls back to
 * the redacted fixture so the demo share link always renders.
 */
export async function fetchPublicReport(
  token: string
): Promise<PublicReportResult> {
  const result = await backendGet(`/r/${token}`);
  if (result.ok) {
    return { status: "ok", report: parseData(publicReportSchema, result.data) };
  }
  if (result.status === 404) {
    return { status: "not_found" };
  }
  if (result.status === 410) {
    return { status: "gone" };
  }
  return { status: "ok", report: publicReportFixture };
}
