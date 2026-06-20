---
title: Frontend organization audit
status: pending
date: 2026-06-16
scope: frontend/src
method: structural scan + next-best-practices skill (RSC, file conventions, data patterns)
---

# Frontend Organization Audit (`frontend/src`)

## Verdict

The frontend is **disciplined and internally consistent**, but it is organized as a
**backend-style layered DDD app that happens to render with Next.js** — not as an
idiomatic App Router project. Two things stand out:

1. **It barely uses React Server Components.** 241/267 presentation files and
   **42/50 `page.tsx` are `"use client"`**. Data is fetched client-side via
   react-query (33 files) through the BFF; only 12 files use `serverHttp`. On
   Next 15 / React 19 this is a client SPA wrapped in Next — it forfeits
   streaming, server data fetching, and smaller client bundles.
2. **The Clean-Architecture/DDD layering (`domain/application/infrastructure/
   presentation`) is over-engineered for a frontend** and largely duplicates the
   backend's own domain (36 entities, 22 repository *interfaces*, 18 response
   types, plus errors/events/catalogs/enums on the client).

Neither is "broken" — the BFF rule is respected (no direct `apiBaseUrl` leaks
found), imports are absolute, the protected layout is a proper async Server
Component. But the structure is heavier than recommended and the rendering model
fights the framework. Below, ranked by impact.

---

## What's good (keep)

- **BFF discipline enforced**: zero client modules hitting `Settings.apiBaseUrl` /
  `NEXT_PUBLIC_BACKEND`. Login → `/api/auth/login` → `serverHttp` is the reference.
- **Route groups** `(protected)` / `(public)` are correct and clean.
- **Protected layout** does server-side refresh via `serverHttp` + cookies — exactly right.
- **Absolute imports** consistently used.
- HTTP repositories already replaced most mocks (23 http- vs 8 mock-).

---

## Findings (ranked)

### 🔴 1. Pages are client shells; RSC unused
`page.tsx` files are `"use client"` and render `<AppShell><FeatureView/></AppShell>`;
the View is `"use client"` + react-query. Example: `workflows/page.tsx` → `WorkflowsView`.
**Recommended (Next.js):** `page.tsx` should be a **Server Component** that fetches
initial data (`serverHttp`) and passes it to a client view, or streams via `<Suspense>`.
Keep `"use client"` only on the interactive leaf. This is the single highest-leverage change.
- Move per-route auth/permission gating into the route (Server) instead of a client
  `<PermissionGuard>` wrapper inside every page (`permissions/page.tsx` is 766 lines, client).

### 🟠 2. DDD layering is too heavy for the client
`domain/` carries 22 repository *interfaces* + http impls in `infrastructure/` — a
ports-and-adapters indirection that mostly mirrors the backend. For a Next app the
recommended shape is **feature-colocated** data access (server fetchers + react-query
hooks), not abstract repositories on the client.
- Not asking to rip it out, but: new features shouldn't pay the
  entity→repo-interface→http-repo→mapper tax unless it earns its keep.

### 🟠 3. No route colocation — central `presentation/` mirrors the route tree
Zero `_components` folders inside `app/`. Instead `presentation/workflows` (110 files)
and `presentation/pipelines` (22) duplicate the `app/(protected)/workflows/...` tree.
Two parallel hierarchies drift apart.
**Recommended:** colocate route-specific UI under `app/(protected)/<route>/_components/`;
reserve a top-level folder only for *cross-route* shared UI.

### 🟠 4. `presentation/components` (104 files) mixes primitives with feature UI
`components/ui` (shadcn primitives) sits next to feature components
(`doctype-field`, `validation-rule-modal`, `prompt-editor`, `json-schema-builder`,
`workflow-rule-*`). Design-system primitives and domain components should not share a bucket.
**Recommended:** `components/ui` = design system only; move feature components next to
their feature (or `presentation/<feature>/`).

### 🟡 5. Three overlapping utility buckets
`application/lib` (15 files: formatters, `cn`, `case-noun`, …), `application/helpers`
(2: jwt, session), `src/utils` (1: http-error-handler) — plus `domain/constants`,
`domain/catalogs`. Same role, three+ homes. Consolidate into one `lib/` (or
`application/lib`) with sub-namespaces (`format/`, `auth/`).

### 🟡 6. `i18n` split / mislabel
`src/i18n` (next-intl config + messages) is the correct home. `application/i18n/pdf-viewer.ts`
is just constants mislabeled as i18n — move to the pdf feature.

### 🟡 7. Route naming drift & stale routes
- Mixed casing: `(public)/reset_password` (snake) vs `api/auth/reset-password` (kebab);
  dynamic `[wf_slug]` (snake). Next convention is **kebab-case** routes.
- Likely-stale/overlapping routes: `data-sources`, `integrations`, **and** `connections`
  (memory: "Conexiones replaces Integrations") — confirm which are live and delete the rest.

### 🟡 8. `staff` vs `superuser` duplication
`app/staff` (outside the route groups), `presentation/staff` (7) **and**
`presentation/superuser` (7). Clarify the distinction or merge; an `(staff)` route group
would be more consistent than a bare `app/staff`.

### 🟡 9. Path alias forces `@/src/...` everywhere
`tsconfig` maps `@/* → ./*`, so every import is `@/src/presentation/...`. The common
convention is `@/* → ./src/*` so you write `@/presentation/...`. Cosmetic, but it leaks
`src/` into ~all imports. (Changing it is a repo-wide codemod — low priority.)

### ⚪ 10. Test placement — actually consistent (corrected after deep review)
Deep review: all 8 `*.test.ts(x)` are **colocated** (consistent policy); `.spec.ts` = Playwright e2e
under `e2e/`; `src/test` is only a vitest **setup** dir, not a stray test home. No action needed —
coverage is sparse (8 files) but placement is fine.

### ⚪ 11. Stale docs
`CLAUDE.md` says infrastructure is "mock repositories (API integration pending)" — no
longer true (mostly HTTP). Update.

---

## Recommended target shape (incremental, not a rewrite)

```
src/
  app/
    (protected)/<route>/
      page.tsx            # Server Component: fetch + gate, stream via Suspense
      _components/        # route-local client UI (colocated)
  components/
    ui/                   # design system (shadcn) ONLY
  features/<feature>/     # (optional) cross-route feature: hooks, api, components
  lib/                    # one util home (format/, auth/, http/)
  domain/                 # keep ONLY types/entities actually shared; drop unused repo interfaces over time
  infrastructure/http/    # serverHttp/authHttp + BFF clients
  i18n/                   # next-intl config + messages (single home)
```

### Suggested sequencing
1. **Cheap wins first:** consolidate utils → `lib/`; fix i18n mislabel; update stale
   `CLAUDE.md`; pick a test policy; delete confirmed-dead routes; normalize route casing.
2. **Split `components/`:** primitives (`ui/`) vs feature components.
3. **RSC pilot:** convert 1–2 read-heavy pages (e.g. dashboard, workflows list) to Server
   Components that fetch initial data with `serverHttp` and hydrate the client view. Measure
   bundle + TTFB, then roll the pattern out. This is the highest-value change.
4. **Re-evaluate DDD layering** per feature as you touch it; stop adding repo interfaces
   on the client unless a feature truly needs the seam.

> Note: items 1–2, 6–11 are low-risk reorganizations. Item 3 (RSC) is the strategic one
> and should be piloted, not big-banged.
