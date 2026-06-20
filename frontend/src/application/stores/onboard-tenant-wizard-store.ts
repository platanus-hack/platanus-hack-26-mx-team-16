/**
 * Ephemeral state for the "Registrar Tenant" wizard. NOT persisted —
 * the store is reset every time the dialog opens so a half-finished
 * draft from a previous session never leaks into a new attempt.
 */

import { create } from "zustand";

export type WizardStep = "info" | "members" | "verify";

export type MemberRoleSlug = "admin" | "member";

export interface DraftMember {
  /** stable client id; allows updating rows in place */
  rowId: string;
  email: string;
  roleSlug: MemberRoleSlug;
}

export interface InvitationResult {
  email: string;
  /** Server-issued token; powers the copy-link button. */
  token: string;
  status: string;
  expiresAt: string | null;
}

export interface OnboardingTenantResult {
  tenantId: string;
  tenantName: string;
  tenantSlug: string;
  invitations: InvitationResult[];
}

/** Pure data slice — never overwrite the actions on the store. */
interface OnboardTenantWizardData {
  open: boolean;
  step: WizardStep;

  // step 1 — info
  name: string;
  countryCode: string;
  currencyCode: string;
  timeZone: string;
  industryId: string | null;

  // step 2 — members
  members: DraftMember[];
  skipEmail: boolean;

  // submit + verify
  isSubmitting: boolean;
  error: string | null;
  result: OnboardingTenantResult | null;
}

interface OnboardTenantWizardActions {
  openWizard: (defaults: {
    countryCode: string;
    currencyCode: string;
    timeZone: string;
  }) => void;
  close: () => void;
  setStep: (step: WizardStep) => void;
  setName: (name: string) => void;
  setCountryCode: (code: string) => void;
  setCurrencyCode: (code: string) => void;
  setTimeZone: (tz: string) => void;
  setIndustryId: (id: string | null) => void;
  addMember: () => void;
  updateMember: (rowId: string, patch: Partial<DraftMember>) => void;
  removeMember: (rowId: string) => void;
  setSkipEmail: (skip: boolean) => void;
  beginSubmit: () => void;
  setError: (message: string | null) => void;
  setResult: (result: OnboardingTenantResult) => void;
}

type OnboardTenantWizardState = OnboardTenantWizardData &
  OnboardTenantWizardActions;

const newRowId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `m_${Math.random().toString(36).slice(2)}`;

const emptyMember = (): DraftMember => ({
  rowId: newRowId(),
  email: "",
  roleSlug: "member",
});

const INITIAL_DATA: OnboardTenantWizardData = {
  open: false,
  step: "info",
  name: "",
  countryCode: "",
  currencyCode: "",
  timeZone: "",
  industryId: null,
  members: [],
  skipEmail: false,
  isSubmitting: false,
  error: null,
  result: null,
};

export const useOnboardTenantWizardStore = create<OnboardTenantWizardState>(
  (set) => ({
    ...INITIAL_DATA,

    openWizard: (defaults) =>
      set({
        ...INITIAL_DATA,
        open: true,
        countryCode: defaults.countryCode,
        currencyCode: defaults.currencyCode,
        timeZone: defaults.timeZone,
        members: [emptyMember()],
      }),
    close: () => set({ ...INITIAL_DATA }),
    setStep: (step) => set({ step }),
    setName: (name) => set({ name }),
    setCountryCode: (countryCode) => set({ countryCode }),
    setCurrencyCode: (currencyCode) => set({ currencyCode }),
    setTimeZone: (timeZone) => set({ timeZone }),
    setIndustryId: (industryId) => set({ industryId }),
    addMember: () =>
      set((s) => ({ members: [...s.members, emptyMember()] })),
    updateMember: (rowId, patch) =>
      set((s) => ({
        members: s.members.map((m) =>
          m.rowId === rowId ? { ...m, ...patch } : m,
        ),
      })),
    removeMember: (rowId) =>
      set((s) => ({ members: s.members.filter((m) => m.rowId !== rowId) })),
    setSkipEmail: (skipEmail) => set({ skipEmail }),
    beginSubmit: () => set({ isSubmitting: true, error: null }),
    setError: (message) => set({ isSubmitting: false, error: message }),
    setResult: (result) =>
      set({ isSubmitting: false, error: null, result, step: "verify" }),
  }),
);
