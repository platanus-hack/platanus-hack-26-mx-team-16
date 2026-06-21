/**
 * Scan form schema (§F5) — URL + level + attestation. This is the legal control
 * expressed as a form. Validation here is UX only; the authoritative SSRF /
 * attestation invariant lives in the backend (01-legal-ethics §2.4).
 *
 * Rules:
 * - `basico` (passive, anonymous, default) → attestation gate hidden, `authorized=false`.
 * - active levels (`intermedio`/`avanzado`) → gate visible; `authorized` MUST be true.
 */
import { z } from "zod";

import { isLikelyPublicHost, normalizeUrl } from "../lib/url";
import { scanLevelSchema } from "./api";

export const scanFormSchema = z
  .object({
    /** Raw URL text the user typed (normalized on submit). */
    url: z
      .string()
      .trim()
      .min(1, "Ingresa una URL")
      .refine((v) => normalizeUrl(v) !== null, {
        message: "URL inválida",
      })
      .refine((v) => isLikelyPublicHost(v), {
        // Rejects localhost / private IPs / hostnames without a dot. UX guard only.
        message: "Solo dominios públicos (no IPs privadas ni localhost)",
      }),
    level: scanLevelSchema.default("basico"),
    /** Attestation checkbox. Required for active levels. */
    authorized: z.boolean().default(false),
  })
  .refine(
    (data) => data.level === "basico" || data.authorized === true,
    {
      message: "Debes declarar que tienes autorización para auditar este dominio",
      path: ["authorized"],
    }
  );

/** Resolved (output) values — `.default()` fields are required here. */
export type ScanFormValues = z.infer<typeof scanFormSchema>;
/** Raw (input) values for react-hook-form fields — `.default()` fields optional. */
export type ScanFormInput = z.input<typeof scanFormSchema>;

/** Body sent to POST /api/scans (after normalization). */
export type ScanRequestBody = {
  url: string;
  level: z.infer<typeof scanLevelSchema>;
  authorized: boolean;
};
