---
title: Frontend reorganization — implementation plan
status: pending
date: 2026-06-16
feature: frontend-reorg
scope: frontend/src
audit: product/_reorg/FRONTEND-ORG-AUDIT.md
method: deep review (4 parallel slice/route/component/cross-cutting traces) + next-best-practices
---

# Frontend Reorg — Implementation Plan

Phased, pragmatic. Each phase is independently shippable; later phases assume
earlier ones landed. Evidence is from a code-level deep review, not the surface scan.

## Locked decisions (Vic, 2026-06-16)

1. **Scope:** phased & pragmatic — cleanup → structural reorg → RSC pilot. No big-bang.
2. **`integrations` vs `connections` vocabulary:** **OUT OF SCOPE** here; documented only,
   handled separately. (Code currently: org `/integrations` canonical with `/connections`
   redirect; workflow `connections` canonical with `integrations` redirect — inverted across scopes.)
3. **DDD repo layer:** **keep, don't grow.** Existing `domain/repositories` + `infrastructure/
   repositories/http-*` stay untouched. **New features call `serverHttp`/`authHttp` from hooks
   directly — no new repo interfaces.** This becomes a documented convention (Phase 1 docs task).

## Out of scope (explicit)

- Renaming/unifying integrations↔connections.
- Collapsing the DDD repository seam (we keep it; only stop adding to it).
- Broad RSC rollout (gated on the Phase 3 pilot measurement).
- The ~36 `presentation/` files with hardcoded Spanish literals (separate i18n-completeness pass).
- Any backend change.

---

## Phase 1 — Cleanup (low risk, high return)

**Goal:** delete dead code, dedupe, normalize casing, fix stale docs. No behavior change.
Suggested PR split: (1a) deletions, (1b) casing renames, (1c) i18n + docs.

### 1a. Dead-code deletions
Confirmed dead via import-site tracing (0 reachable importers):

- **Routes:** `app/(protected)/doctypes/page.tsx` + `app/(protected)/doctypes/[doctypeId]/page.tsx`
  — orphaned org mirror of the workflow-scoped `document-types` (no inbound nav link).
  → Deleting this also makes `mock-doctype.ts` dead (it was its only consumer).
- **Mock repos** (`infrastructure/repositories/`): `mock-case.ts`, `mock-member.ts` (hard dead);
  `mock-doctype.ts` (dead after route deletion above); `mock-workflow.ts` + `mock-workflow-config.ts`
  (dead via orphaned store, below).
  → **Keep alive (still backing UI, real-API pending):** `mock-billing.ts`, `mock-knowledge.ts`,
  `mock-document.ts`. Track these as "pending API integration."
- **Orphaned stores** (`application/stores/`): `workflow-steps-store.ts`, `use-billing-store.ts` (0 importers).
- **Demo files:** `presentation/components/component-example.tsx`, `presentation/components/example.tsx`.
- **Duplicates:** dedupe `empty-state` (top-level `components/empty-state.tsx` vs `components/common/empty-state.tsx`)
  to a single source; dedupe `json-viewer.tsx` (top-level vs `components/ui/json-viewer.tsx`) to the `ui/` one.
- **Unused util:** `application/lib/format-timestamp.ts` (0 imports).

**Verify-first deletions** (grep 0 imports immediately before `rm`, do NOT blind-delete):
`presentation/components/schema-builder/` (7 files — likely superseded by `json-schema-builder/`),
`presentation/components/detail-pane-layout.tsx`, `presentation/components/doctype-field.tsx`,
`presentation/components/icons/documents-icon.tsx`.

### 1b. Route casing normalization (kebab/camel, the lone snake_case offenders)
- `app/(public)/reset_password` → `reset-password` (+ `[token]`). Update internal links/`router.push`
  (the API route is already `api/auth/reset-password`).
- Dynamic param `[wf_slug]` → `[wfSlug]` across `app/(protected)/workflows/[wf_slug]/**` and every
  `useParams()`/string read. **Isolate in its own commit** — touches many route files; grep all `wf_slug`.

### 1c. i18n debt + docs
- Migrate the 3 consumers of `application/i18n/pdf-viewer.ts` to next-intl (add a `PdfViewer` namespace
  to `i18n/messages/{en,es}.json`), then delete the file. Consumers:
  `presentation/workflows/documents/document-viewer-pane.tsx`,
  `presentation/components/ui/pdf-viewer-loading.tsx`, `presentation/components/ui/pdf-viewer.tsx`.
- **Docs:** update `frontend/CLAUDE.md` — infrastructure is HTTP-backed (not "mock repositories pending");
  list the 3 features still on mocks; **add the "new features: hooks→serverHttp/authHttp directly, no new
  repo interfaces" convention** (locked decision #3).

**Verification (all phases):** `pnpm tsc --noEmit`, `biome check`, `vitest run`, `pnpm build`,
Playwright smoke on affected routes (workflows, doctype/document-types, reset-password, pdf viewer).

---

## Phase 2 — Structural reorg (medium risk, mechanical)

**Goal:** primitives vs feature components separated; one utility home; one provider tree.
Heavy on import-path churn → use scripted codemods + per-area commits. Move-map in Appendix A.
PR split: (2a) component moves, (2b) lib consolidation + `cn` codemod, (2c) providers.

### 2a. Split `presentation/components` (104 files)
- `components/ui/` = design-system primitives only (43 files, already shadcn-style). Fold the deduped
  `empty-state` + `json-viewer` in here.
- **Move feature components to their feature folder** (project convention `presentation/<feature>/`):
  - doctype/schema-form set → `presentation/workflows/document-types/`
    (`doctype-field-row`, `field-detail`, `field-type-meta`, `sortable-field-row`,
    `json-schema-driven-form`, `common/doctype-operations-widget`).
  - rules/prompt set → `presentation/workflows/rules/`
    (`prompt-editor`, `prompt-highlight`, `validation-rule`, `validation-rule-detail`,
    `workflow-rule-modal`, `workflow-rule-import-modal`, `workflow-rule-compilation-section`,
    `workflow-rule-derivation-editor`).
  - `auth-container.tsx` → `presentation/auth/`.
- Generic cross-feature pieces (`components/common/*` rows/filters/labels, `locale-switcher`,
  `filters/`, `json-schema-builder/`) stay in `presentation/components/` as the shared library.
  Rename intent: `presentation/components/` = shared/reusable; `presentation/common/` = app-shell/
  providers/guards (leave as is) — keep the two "common"s distinct and documented.

### 2b. Consolidate utilities → `src/lib/`
Collapse `application/lib` + `application/helpers` + `src/utils` into one `src/lib/` (Appendix B):
- `lib/format/` (date, duration, confidence, document, markdown, id, case-noun + its colocated test)
- `lib/http/error-handler.ts`, `lib/auth/{session,jwt-token}.ts`
- Feature-specific (`workflow-rule-kinds*`, `mapped-extraction`) → **colocate** under
  `presentation/workflows/lib/` (4/5 are single-use), not a global bucket.
- **`cn`**: `application/lib/utils.ts` → `src/lib/cn.ts`. **102 import sites** — own commit, scripted
  find/replace, verify `tsc` clean after.

### 2c. Consolidate providers
- New `application/providers/app-providers.tsx` composing
  `NextIntlClientProvider → ThemeProvider → QueryProvider → SessionProvider`.
- Root `app/layout.tsx` renders `<AppProviders>{children}</AppProviders>` instead of 4 inline nested tags.
  (Optionally re-home `ThemeProvider` from `presentation/common/` and `SessionProvider` from
  `application/contexts/` into `application/providers/`; low priority.)

---

## Phase 3 — RSC pilot: workflows list (additive, single PR)

**Goal:** prove the Server-Component + prefetch + hydrate pattern on the cleanest slice, then decide
rollout from real numbers. Feasibility = GO (no hard blocker; the gap is missing infra).

### Build the missing infra
- **NEW `application/providers/get-query-client.ts`** — `cache()`-wrapped per-request `QueryClient`
  factory for the server + browser singleton (react-query's documented RSC pattern). Today there is
  zero `HydrationBoundary`/`dehydrate`/`prefetchQuery` and a single root `QueryClientProvider`.
- **NEW server auth-fetch helper** — `serverHttp` has **no auth interceptor**; the client path relies on
  `authHttp`→`proxy.ts` (injects `X-Api-Key`) + zustand Bearer/X-Tenant, none of which run in an RSC.
  Add `serverAuthHttp()` (or `getWorkflowsServer()`) that reads `cookies()` (access token `___AT5___`)
  + tenant slug and calls the backend with explicit `getCommonHeaders(slug, token)`
  (`Authorization: Bearer` + `X-Tenant` + server-only `X-Api-Key`). The `(protected)/layout.tsx`
  (`force-dynamic`) already exposes `session.accessToken` + `tenant.slug` — reuse that plumbing.

### The change
- `app/(protected)/workflows/page.tsx`: drop `"use client"`; make `async`; build request-scoped
  `QueryClient`; `prefetchQuery(queryKeys.workflows.all)`; wrap `<WorkflowsView/>` in
  `<HydrationBoundary state={dehydrate(qc)}>`. `AppShell`/`PermissionGuard` remain client children.
- `presentation/workflows/workflows-view.tsx`: **unchanged** — `useWorkflowsQuery` (same query key)
  auto-reads the dehydrated cache.
- **Stretch (optional):** do the permission check server-side in the page (read session →
  `forbidden()`), since `PermissionGuard` is client-only, flashes content post-render, and doesn't
  block data. Aligns with the audit's gating finding.

### Acceptance + decision gate
- Workflows list renders with data on first paint (no loading-spinner flash, view-source has the data),
  no hydration mismatch; mutations/refetch still work via the existing hook.
- **Measure** route client-bundle delta + TTFB/LCP before/after; record the numbers in this file.
- If bundle ↓ and TTFB acceptable → write a short `frontend-rsc-rollout` follow-up listing next candidates
  (dashboard, review, usage — read-heavy). If not → stop at the pilot. **Rollout is gated, not assumed.**

---

## Risks & sequencing

- **`[wf_slug]`→`[wfSlug]`** and the **`cn` 102-site** change are the two biggest churn items — each gets
  its own scripted commit, verified with `tsc` before merge.
- Verify-first deletions must re-confirm 0 imports at execution time (index may have shifted).
- Phase 2 import-path churn is wide but mechanical; rely on `tsc` + `biome` + `vitest` + a Playwright smoke
  as the safety net per commit.
- Phases are independent PRs; nothing here requires backend coordination except Phase 3's server fetch,
  which only reuses existing headers/cookies (no new backend surface).

---

## Appendix A — component move-map (condensed)

DELETE: `component-example`, `example`, `components/common/empty-state` (dup), top-level `json-viewer` (dup).
VERIFY-THEN-DELETE: `schema-builder/`, `detail-pane-layout`, `doctype-field`, `icons/documents-icon`.
→ `components/ui/`: `empty-state` (deduped), `json-viewer` (deduped).
→ `presentation/workflows/document-types/`: `doctype-field-row`, `field-detail`, `field-type-meta`,
  `sortable-field-row`, `json-schema-driven-form`, `common/doctype-operations-widget`.
→ `presentation/workflows/rules/`: `prompt-editor`, `prompt-highlight`, `validation-rule(+detail)`,
  `workflow-rule-modal`, `workflow-rule-import-modal`, `workflow-rule-compilation-section`,
  `workflow-rule-derivation-editor`.
→ `presentation/auth/`: `auth-container`.
STAY (shared): `components/common/*` (generic rows/filters/labels), `locale-switcher`, `filters/`,
  `json-schema-builder/`, `components/ui/*`.

## Appendix B — utility consolidation map

```
src/lib/
  cn.ts                 ← application/lib/utils.ts        (102 sites; codemod)
  format/
    date.ts             ← format-date-time + format-relative-date + calendar-utils
    duration.ts         ← format-duration
    confidence.ts       ← format-confidence
    document.ts         ← document-format
    markdown.ts         ← strip-markdown
    id.ts               ← short-uuid
    case-noun.ts(+.test) ← case-noun(+.test)
  http/error-handler.ts ← src/utils/http-error-handler.ts
  auth/session.ts       ← application/helpers/session.ts
  auth/jwt-token.ts     ← application/helpers/jwt-token.ts
DELETE: application/lib/format-timestamp.ts (0 imports)
COLOCATE (not global): workflow-rule-kinds(+bootstrap), mapped-extraction → presentation/workflows/lib/
```
