/**
 * Scan form store (§F5) — the URL + level + attestation state for <ScanForm>,
 * modeled as a per-instance zustand store rather than react-hook-form.
 *
 * Why a store (and why per-instance):
 *  - The form is mounted twice — the `/scan` page AND the modal from `/`. A
 *    global singleton would leak a half-typed URL between the two (and across
 *    navigations), so each <ScanForm> creates its own store via
 *    `createScanFormStore(initialUrl)` and provides it through context.
 *  - Fields subscribe to their OWN slice (`useScanFormStore(selector)`), so a
 *    keystroke in the URL field re-renders ONLY that field — not the level
 *    cards, the attestation gate, or the submit button. This is what kills the
 *    "type → whole page re-renders → input loses focus" bug.
 *
 * Validation is zod (`scanFormSchema`) run on submit via `validate()`. Field
 * errors clear as the user edits the offending field.
 */
import { createContext, useContext } from "react";
import { useStore } from "zustand";
import { createStore } from "zustand/vanilla";

import { extractHost, normalizeUrl } from "@/src/application/owliver/lib/url";
import type { ScanLevel } from "@/src/application/owliver/schemas/api";
import {
  type ScanRequestBody,
  scanFormSchema,
} from "@/src/application/owliver/schemas/scan-form";

/** Inline, per-field validation messages (zod issues mapped by path). */
export type ScanFormErrors = {
  url?: string;
  authorized?: string;
};

type ScanFormData = {
  /** Raw URL text the user is typing (normalized only on submit). */
  url: string;
  level: ScanLevel;
  authorized: boolean;
  errors: ScanFormErrors;
};

type ScanFormActions = {
  setUrl: (url: string) => void;
  setLevel: (level: ScanLevel) => void;
  setAuthorized: (authorized: boolean) => void;
  /**
   * Validate the current values. On success returns the normalized request
   * body ready for POST /api/owliver/scans; on failure sets `errors` and
   * returns null.
   */
  validate: () => ScanRequestBody | null;
};

export type ScanFormState = ScanFormData & ScanFormActions;

export type ScanFormStore = ReturnType<typeof createScanFormStore>;

export function createScanFormStore(initialUrl = "") {
  return createStore<ScanFormState>((set, get) => ({
    url: initialUrl,
    level: "basico",
    authorized: false,
    errors: {},

    setUrl: (url) =>
      set((s) =>
        // Clear a stale url error as soon as the user edits the field.
        s.errors.url
          ? { url, errors: { ...s.errors, url: undefined } }
          : { url }
      ),

    setLevel: (level) =>
      set(() =>
        // Switching to `basico` resets attestation so a stale `true` never
        // leaks across a level change; also drops the attestation error.
        level === "basico"
          ? { level, authorized: false, errors: {} }
          : { level }
      ),

    setAuthorized: (authorized) =>
      set((s) => ({
        authorized,
        errors: { ...s.errors, authorized: undefined },
      })),

    validate: () => {
      const { url, level, authorized } = get();
      const parsed = scanFormSchema.safeParse({ url, level, authorized });

      if (!parsed.success) {
        const errors: ScanFormErrors = {};
        for (const issue of parsed.error.issues) {
          const key = issue.path[0];
          if (key === "url" && !errors.url) errors.url = issue.message;
          if (key === "authorized" && !errors.authorized) {
            errors.authorized = issue.message;
          }
        }
        set({ errors });
        return null;
      }

      const data = parsed.data;
      const normalized = normalizeUrl(data.url);
      set({ errors: {} });
      return {
        url: normalized ? normalized.toString() : data.url,
        level: data.level,
        // `basico` never attests; active levels carry the checkbox state.
        authorized: data.level === "basico" ? false : data.authorized,
      };
    },
  }));
}

const ScanFormStoreContext = createContext<ScanFormStore | null>(null);

export { ScanFormStoreContext };

/**
 * Subscribe to a slice of the nearest <ScanForm> store. Returning primitives
 * (or stable action refs) keeps re-renders scoped to the slice that changed.
 */
export function useScanFormStore<T>(selector: (state: ScanFormState) => T): T {
  const store = useContext(ScanFormStoreContext);
  if (!store) {
    throw new Error(
      "useScanFormStore must be used within a <ScanFormStoreContext.Provider>"
    );
  }
  return useStore(store, selector);
}

/** Read the store handle itself (for deferred reads like submit — no subscription). */
export function useScanFormStoreApi(): ScanFormStore {
  const store = useContext(ScanFormStoreContext);
  if (!store) {
    throw new Error(
      "useScanFormStoreApi must be used within a <ScanFormStoreContext.Provider>"
    );
  }
  return store;
}
