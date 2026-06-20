# Owliver — Spec ↔ Plan ↔ Code Validation Report

**Date:** 2026-06-20
**Scope:** All 13 numbered feature specs (`01`–`13`) × their `spec.md` (QUÉ/PRD) and `plan.md` (CÓMO/implementation). Validation covers three axes: (1) internal spec↔plan↔code consistency within each feature, (2) cross-feature contracts (data-model, attack-levels, scoring, api-contract, realtime-events, agent-scanner, index/status metadata), and (3) accuracy of code references against the actual `backend/`/`frontend/` SaaS foundation.

> **Context:** The pentest engine (modules `scans`, `findings`, `agentic_surface`, `watchlist`, `alerts`, `public_reports`, `scan_events` and the Agno worker) is **specified but not yet implemented** (`status: pending`, `coverage: 0` across all 13 features). That is expected and is **not** an error. Every issue below is a documentation-level contradiction that would mislead an implementer or break the feature's own tests if built verbatim — not a shipped runtime bug.

---

## Executive summary

Overall consistency health is **good**. The specs are internally coherent and the code-reference catalog is overwhelmingly accurate (the SaaS foundation is described faithfully). The defects cluster in three predictable seams:

1. **The gov-passive Nuclei tag set** — a half-applied migration that left two `plan.md` files (01, 04) carrying a stale, invalid `http-misconfig` tag set that contradicts the specs and would break the legal passive-profile gate. This is the single most-cited issue (appears across the 01/02/04 internal and cross-feature dimensions).
2. **The `12-api` error envelope + cursor-pagination reuse** — the plan/spec describe an error shape and "no cursor helper exists" that both contradict the actual foundation code already in `common/`.
3. **Static evidence URL prefix + `scans.summary` column** — cross-feature integration-boundary mismatches between the writer (04/05) and the consumers (06/09/13).

The `AgenticType` hyphen-vs-underscore divergence recurs across several dimensions but reduces to one root fix in `06-data-model`.

### Counts by severity

| Severity | Count |
|----------|-------|
| High     | 5     |
| Medium   | 16    |
| Low      | 23    |
| **Total**| **44**|

> Several near-identical findings were deduplicated below (the gov-passive Nuclei tag set was reported ~4 times across internal + cross-feature dimensions → consolidated into one High entry with a cross-reference note; the `AgenticType` delimiter and `12-api` cursor/error-envelope issues were likewise merged). The raw confirmed-issue list contained 44 verdicts; the consolidated report presents the distinct defects.

---

## High severity

### H1 — Gov-passive Nuclei tag set is invalid/stale in 01-plan and 04-plan
**Features/Dimension:** 01-legal-ethics, 02-attack-levels, 04-scanning-engine · attack-levels / agent-scanner (internal + cross-feature, consolidated)

**Description:** The canonical gov-passive Nuclei `-tags` set is `exposures,misconfiguration,ssl,tech,dns` (fixed in `01-spec §3`, `02-spec §3.1/§4`, and `02`'s `_BASIC_GOV` whitelist, which all explicitly state the invalid `http-misconfig` tag was removed). But two `plan.md` files were never updated: `01-legal-ethics/plan.md:109` freezes `GOV_PASSIVE_PROFILE.nuclei_tags_allow=("ssl","tech","http-misconfig")` — the actual definition of the legal predicate `assert_within_passive_profile` — and `04-scanning-engine/plan.md:263` narrates `resolve_tools` gov-basico output as `nuclei -tags ssl,tech,http-misconfig`. Because `04`'s `resolve_tools` builds the toolset from `02`'s whitelist (the five-tag set) and then validates it against `01`'s frozen allow-list (only `ssl,tech,http-misconfig`), the legal gate would **raise for every gov/básico scan** — the highest-traffic `.gob.mx` ranking path — and the byte-equivalence guards (`02 §10.1`, `01-plan test_passive_profile`) would assert mutually-exclusive sets. `http-misconfig` is also not a valid Nuclei tag (the real one is `misconfiguration`).

**Evidence:**
- `01-legal-ethics/spec.md:131` — `Nuclei limitado a -tags exposures,misconfiguration,ssl,tech,dns`
- `02-attack-levels/spec.md:93` — `Nuclei con -tags exposures,misconfiguration,ssl,tech,dns ... excluyendo intrusive,dos,fuzzing,network`
- `02-attack-levels/backend-attack-levels.md:280` — `los dos specs están unificados (el inválido http-misconfig quedó eliminado)`
- ✗ `01-legal-ethics/plan.md:109` — `nuclei_tags_allow=("ssl", "tech", "http-misconfig")`
- ✗ `04-scanning-engine/plan.md:263` — `nuclei -tags ssl,tech,http-misconfig excluyendo intrusive,dos,fuzzing,network`

**Recommended fix:** **Specs + `02` (whitelist owner) are authoritative** (and the set is Nuclei-valid). Update `01-legal-ethics/plan.md:109` to `nuclei_tags_allow=("exposures","misconfiguration","ssl","tech","dns")` and `04-scanning-engine/plan.md:263` prose to match. This makes `02 §10.1`'s byte-equivalence guard actually pass against `01`'s `assert_within_passive_profile`. Already tracked as item A5 in `PARALLELIZATION-VALIDATION.md`.

---

### H2 — `scans.summary` (JSONB) is consumed by 09 but absent from 06's authoritative schema
**Features/Dimension:** 06-data-model, 09-reporting, 05-agent-team · data-model (cross-feature)

**Description:** `09-reporting`'s render path reads/persists `scans.summary` (serialized `ExecutiveSummary` = narrative + top_risks), and its decision D1 self-labels this **BLOQUEA**. But `06-data-model` — the declared source of truth for the `scans` schema — defines **no `summary` column** in its spec §2 DDL, §3.2 column list, or plan §2.4 `ScanORM` table (`grep`: 0 hits in both 06 files). `05-agent-team` produces the `ExecutiveSummary` but its persist step writes only status/scores/grade/coverage/tools_status — **not** summary. So the column is read by the report path, produced by the worker, yet defined and persisted by no one; ownership is left ambiguous ("la añade 06 o la migración de 05"). Building 06's Alembic migration verbatim yields a `scans` table with no `summary` → the report render (in-app/PDF/public) breaks.

**Evidence:**
- `09-reporting/plan.md:227-229` — `Resumen ejecutivo Opus → scans.summary (JSONB) ... Net-new columna summary JSONB nullable en ScanORM — la añade 06 o la migración de 05`
- `09-reporting/plan.md:451` — `D1 — scans.summary (JSONB) persiste el ExecutiveSummary de Opus`
- ✗ `06-data-model/spec.md:34-48` (scans DDL) and `06-data-model/plan.md:185` (ScanORM columns) — neither contains `summary`

**Recommended fix:** **`06-data-model` is authoritative and must own the column.** Add `summary jsonb NULL` to the spec §2 DDL, the §3.2 column list, the plan §2.4 `ScanORM` table, and the Alembic migration. Then update `09` D1 and `05`'s persist step to reference the 06-owned column rather than treating it as ambiguously net-new.

---

### H3 — Static evidence URL prefix mismatch: writer serves `/static/scans`, consumers expect `/data/scans`
**Features/Dimension:** 04-scanning-engine, 06-data-model, 09-reporting, 13-frontend · api-contract (cross-feature)

**Description:** `04-scanning-engine` (the only writer) persists `evidence.screenshot` as `/static/scans/{id}/{n}.png` and mounts `app.mount("/static/scans", StaticFiles(directory="/data/scans"))`, with a test pinning the `/static/scans` prefix. But three independent consumers expect `/data/scans/...`: `06`'s schema mandates the stored URL be `/data/scans/{scan_id}/{n}.png`, `09`'s PDF renderer mounts `app.mount("/data", ...)` in the **same** `config/main.py` and embeds from `/data/scans/...`, and `13`'s frontend renders from `/data/scans/...`. Two breaks: (1) every persisted evidence URL resolves to a 404 against what the renderer/UI expect; (2) `04` and `09` both claim conflicting static mounts (`/static/scans` vs `/data`) in the same file. The `directory=/data/scans` filesystem path is consistent and is **not** the conflict — the URL prefix is.

**Evidence:**
- `04-scanning-engine/plan.md:366-369` — `guarda la URL relativa (/static/scans/{id}/{n}.png) ... app.mount("/static/scans", StaticFiles(directory="/data/scans"))`
- `06-data-model/spec.md:133` — evidence.screenshot → `/data/scans/{scan_id}/{n}.png`
- `09-reporting/spec.md:68` + `plan.md:128/255` — `/data/scans/{scan_id}/{n}.png`, `app.mount("/data", StaticFiles(directory=settings.DATA_DIR))`
- `13-frontend/spec.md:206` — `/data/scans/{id}/{n}.png`

**Recommended fix:** **`09`/`06` are authoritative** (3 consumers agree on `/data/scans`, only `04` diverges). Make `04` the side that changes: persist evidence URLs as `/data/scans/{id}/{n}.png`, mount `/data` (DATA_DIR-backed), and update `04`'s test. The persisted relative URL and the served mount prefix must be byte-identical.

---

### H4 — Error envelope contract does not match the actual registered handler
**Features/Dimension:** 12-api, 13-frontend · api-contract (cross-feature + internal)

**Description:** `12-api/spec.md` "Formato de error único" mandates `{ "error": { "code", "message", "details": null } }`, `12-api/plan.md §5.1` claims this is "ya resuelto por el fundamento" (existing handler already emits it), and `13-frontend §F12` consumes exactly that shape for its 422/404/410/403 UI mapping. But the actually-registered foundation handler (`error_handlers.py:9-34`) emits `ErrorFeedback(errors=[ErrorItem(code, message)], validation=None)`, and `ApiJSONResponse.render` appends `timestamp` — i.e. the real envelope is `{ "errors": [{code, message}], "validation": ..., "timestamp": ... }`: an `errors` **array** (not a singular `error` object), **no `details` key**, plus unmentioned `validation`/`timestamp`. `rate_limit_handler.py` emits a third, incompatible shape (`error` as a string), so the "formato único" promise is itself false across foundation handlers. A frontend coded per spec (`payload.error.code`/`.details`) breaks against the real backend.

**Evidence:**
- `12-api/spec.md:291-293` — `{ "error": { "code": "", "message": "", "details": null } }`
- `13-frontend/spec.md:254` — `formato único {error:{code,message,details}} (ver [12-api])`
- ✗ `error_handlers.py:10-20` — `ErrorFeedback(errors=[ErrorItem(code, message)], validation=None)`; `rate_limit_handler.py` → `{"error":"rate_limit_exceeded", ...}` (string `error`)

**Recommended fix:** **The implemented foundation handler is authoritative** (the plan commits to reusing it unchanged). Reconcile `12-api/spec` "Formato de error único" and `13-frontend §F12` to consume `errors[0].code`/`errors[0].message` (and `validation` for field errors); drop the `details` key and the singular `error` object. If the singular `{error:{...,details}}` shape is genuinely desired, that is **net-new foundation-handler work**, not "ya resuelto". Also normalize or call out the divergent rate-limit shape.

---

### H5 — `12-api` falsely claims "no cursor helper exists in common"; reinvents existing infra
**Features/Dimension:** 12-api · api-contract (internal, code-reference; consolidated)

**Description:** `12-api/plan.md §5.2` asserts `no existe hoy un helper de cursor en common — confirmado` and proposes a net-new `CursorPage[T]` plus a base64 `{sev}:{id}` cursor. This is false: a complete cursor-pagination stack already lives in `common` and is in production use — `encode_cursor`/`decode_cursor` (Fernet base64 `datetime|uuid`) in `common/application/helpers/pagination.py`; generic `Page[T]` (`next_cursor`, `items`, `apply_presenter()`) + `PageIndex` in `common/domain/entities/common/pagination.py`; auto-serialized by `ApiJSONResponse.is_paginated`. The `tenants` SQL repos already implement the exact `limit+1 → encode_cursor → keyset-WHERE` pattern the plan describes as new. The proposed `CursorPage[T]` duplicates `Page[T]` one-for-one. Following the plan literally builds a redundant parallel stack and emits a different response envelope (`{items, next_cursor}` vs the established `{data, pagination:{nextCursor,limit}, timestamp}`).

**Evidence:**
- ✗ `12-api/plan.md:288-289` — `Helper net-new common/presentation/pagination.py (no existe hoy un helper de cursor en common — confirmado)`
- `common/application/helpers/pagination.py` — `encode_cursor`/`decode_cursor`
- `common/domain/entities/common/pagination.py` — `Page[T]` (next_cursor, items) + `PageIndex` + `Pagination`
- `tenants/.../sql_tenant_user.py` — `if len(orm_instances) == filters.limit + 1: next_cursor = encode_cursor(last.created_at, last.uuid)`

**Recommended fix:** **Existing `common` infra is authoritative.** Reuse `Page[T]` + `encode_cursor`/`decode_cursor`, which `ApiJSONResponse` already serializes; drop the false "no existe … confirmado" claim. The only genuine gap is a composite `(severity, id)` cursor for findings ordering — an **extension** of the existing codec, not a net-new `CursorPage`. (Note: the proposed `common/presentation/pagination.py` path is itself legitimately net-new; the defect is the false non-existence claim and the duplicate abstraction.)

---

## Medium severity

> Grouped: **cross-feature** first, then **internal**.

### Cross-feature

### M1 — `AgenticType` enum: hyphens vs underscores disagree across 06 (spec vs plan) and 03
**Features/Dimension:** 06-data-model, 03-agentic-surface, 05-agent-team · data-model / index-status-meta (consolidated)

**Description:** The `AgenticType` value set is spelled two incompatible ways. `06-data-model/spec.md` (authoritative DDL + frozen `AgenticResult` contract) uses **hyphens** (`chatbot | prompt-input | search-ai`) at lines 146/148/238; `06-data-model/plan.md:101` defines `class AgenticType(BaseEnum)` with **underscores** (`prompt_input | search_ai`) and declares its enums the source of truth "verbatim" with the DDL — so 06's own spec and plan contradict each other. The underscore form propagated to `03-agentic-surface/plan.md` (the producer, lines 40/237/476, emits `type=prompt_input`); the hyphen form to `05-agent-team/spec.md:44`. Because `agentic_surface.type` is a persisted column, the two forms are distinct, non-interchangeable values; a consumer comparing against `"prompt-input"` would silently miss a row written `prompt_input`.

**Evidence:**
- `06-data-model/spec.md:148` — `type — chatbot | prompt-input | search-ai`; `:238` — `type: str  # chatbot | prompt-input | search-ai`
- ✗ `06-data-model/plan.md:101` — `class AgenticType(BaseEnum): chatbot | prompt_input | search_ai  # §3.4`
- `03-agentic-surface/plan.md:237` — `emite AgenticSurface(type=prompt_input, ...)`

**Recommended fix:** **`06` owns the enum; standardize on underscores** (matches every other 06 enum — `ScanStatus`, `FindingSeverity`, `AgenticStatus`'s `detected_not_tested` — and the worker code in 03). Correct `06-data-model/spec.md:146/148/238` and `05-agent-team/spec.md:44`. Mitigant: the field is `type: str` (free string, not a `Literal`), so no validation raises today; already triaged "minor-mismatch" in `PARALLELIZATION-VALIDATION.md:30`. The sibling `AgenticStatus` enum is confirmed consistent (underscores).

### M2 — `03`/`05` disagree on the agentic member's tool set and runner model
**Features/Dimension:** 03-agentic-surface, 05-agent-team · agent-scanner / cross-spec (consolidated)

**Description:** For the shared path `src/scans/worker/tools/agentic.py`, `05-agent-team` (spec §1/§2.1, plan §1 line 110/§2.1/§5) names the agentic tools `crawl_site/classify_dom_llm/fingerprint_vendors/run_promptfoo/run_garak` and treats `run_garak`/`run_promptfoo` as first-class wrapper tools. But `03-agentic-surface` — the authoritative owner of the agentic surface — defines `agentic.py` as exactly two closures `make_detect_surface`/`make_probe_agentic` and **freezes the opposite decision**: garak/promptfoo are NOT the runner; the bridge is Playwright-native (CAMINO A), with garak/promptfoo demoted to opt-in CAMINO B fallback, never on `.gob.mx`. An implementer wiring `members.py` from `05` verbatim would build a garak/promptfoo-runner agentic agent, violating 03's frozen design. The path reservation itself is consistent; the runner model and tool inventory are not.

**Evidence:**
- ✗ `05-agent-team/plan.md:110` — `agentic.py  # crawl_site/classify_dom_llm/fingerprint_vendors/run_promptfoo/run_garak`
- `03-agentic-surface/plan.md:129/156` — `tools/agentic.py ... make_detect_surface / make_probe_agentic (closures, 05 §2)`

**Recommended fix:** **`03` is authoritative for the agentic surface.** Align `05`'s agentic-tool inventory (spec §1/§2.1, plan §1/§2.1/§5) to 03's two-closure / Playwright-as-runner model, or explicitly mark `05`'s garak/promptfoo listing as the CAMINO-B-only fallback that 03 owns. `classify_dom_llm`/`fingerprint_vendors` belong in `agentic/detector.py` per 03, not `tools/agentic.py`.

### M3 — `security-headers` tool token: hyphen vs `ToolId` underscore value breaks the passive allow-list
**Features/Dimension:** 01-legal-ethics, 02-attack-levels · index-status-meta / naming (consolidated)

**Description:** `ToolId.SECURITY_HEADERS = "security_headers"` (underscore StrEnum value, `02-attack-levels/backend-attack-levels.md:129`) is the canonical token materialized into `ToolInvocation.tool`, but `GOV_PASSIVE_PROFILE.tools` in `01-legal-ethics/plan.md:108` lists it as `"security-headers"` (hyphen) inside the frozenset that `assert_within_passive_profile(Iterable[ToolInvocation])` compares against. Since resolved invocations carry `"security_headers"`, the membership check fails (`"security_headers" not in {"security-headers", ...}`), so the gov passive security-headers tool is falsely rejected (fail-closed over-block), breaking `test_passive_profile.py` / the §10.1 byte-identity guard. The other three tokens (`testssl`/`whatweb`/`nuclei`) match coincidentally, isolating the defect to this one token (lifted from the informal trailing comment `# security-headers / Observatory`).

**Evidence:**
- ✗ `01-legal-ethics/plan.md:108` — `tools=frozenset({"testssl", "security-headers", "whatweb", "nuclei"})`
- `02-attack-levels/backend-attack-levels.md:129` — `SECURITY_HEADERS = "security_headers"   # security-headers / Observatory`

**Recommended fix:** **`02` owns `ToolId`; `"security_headers"` (underscore) is authoritative.** Change the single frozenset entry in `01-legal-ethics/plan.md:108` to `"security_headers"` (or author the frozenset from `ToolId` members). The 04 references at lines 227/263 are prose labels, not comparison keys, and need not change.

### M4 — `/me/alerts` module ownership: 12 assigns `scans`, 08 places use cases in `sites`
**Features/Dimension:** 12-api, 08-ranking-watchlists · api-contract (cross-feature)

**Description:** The two net-new alert-prefs use cases (`get_alert_prefs.py`/`update_alert_prefs.py`, backing `GET/PUT /me/alerts`) are placed in different modules. `12-api/plan.md §1` (the endpoint→module authority) assigns them to `src/scans/` (use-case list, router table `Router=scans`, `me_router` on `scans_router`, prose "/me/alerts en src/scans/"). `08-ranking-watchlists/plan.md §2.2` places them in `src/sites/application/use_cases/` (table header + row + test under `tests/sites/`), consistent with `06-data-model/plan.md:65` which assigns `notification_prefs` + `NotificationPrefsRepository` to `src/sites/`. The HTTP contract is identical, so only the owning module differs — but `12`'s `scans` placement also violates the stated `sites`-does-not-depend-on-`scans` direction (a `scans` use case would import a `sites`-owned repository). `08` is additionally self-contradictory: its line 88 says `/me/alerts` is assigned to `scans` per 12.

**Evidence:**
- `12-api/plan.md:97-98` — `| GET /me/alerts | GetAlertPrefs | ... | scans | auth |` (+ files under `src/scans/`)
- `08-ranking-watchlists/plan.md:128-134` — table header `Use case (src/sites/application/use_cases/)` with `get_alert_prefs.py` / `update_alert_prefs.py`

**Recommended fix:** **Pick one owner;** `06` (data-model authority) implies `src/sites/`. Align `12 §1` (file list, routing-table module column, prose, router location) and `08 §2.2` + its test path. Since `12-api` is the declared endpoint→module authority but `06` owns `notification_prefs` in `sites`, the cleanest resolution is `sites` (update `12` to module `sites`); alternatively move the prefs repo to `scans`.

### M3a — `ScanEvent.progress` field exists in 10's contract but not in 06's `scan_events` table
**Features/Dimension:** 10-realtime-live-view, 06-data-model · realtime-events (cross-feature)

**Description:** `10` adds a top-level `progress: int | None` field to the `ScanEvent` schema (spec §2 line 52; plan §2.1 line 152) and asserts the shape is "1:1 con la tabla `scan_events`" frozen by `06`. But `06` — the freeze-owner — declares no `progress` on `scan_events`: its spec §2/§3.5 DDL and plan §2.4 `ScanEventORM` enumerate columns ending at `payload jsonb`, no `progress` (it exists only on the `scans` table). The "1:1" claim is false; an implementer freezing `events.py` from 06 omits `progress`, breaking 10's theater progress bar. 10's §2.2 coordination list asks 06 only for `next_seq` + a cursor reader, never `progress`.

**Evidence:**
- `10-realtime-live-view/plan.md:152` — `progress: int | None = None   # 0–100, en phase (y opc. score) → barra header`; `:137` — "1:1 con la tabla scan_events"
- ✗ `06-data-model/spec.md:76` / `plan.md:188` — `scan_events(... message, payload jsonb)`, no `progress`

**Recommended fix:** **`06` owns the contract.** Either add `progress int | None` to `06`'s `events.py` contract + `scan_events` table (preferred — replay needs it typed), or `10` carries `progress` inside the existing `payload jsonb` and stops listing it as a top-level field. (Severity is at the lower end of medium: `progress`/`current_phase` already exist on the `scans` row, so data is recoverable.)

### Internal

### M5 — `07-scoring`: `ScoreResult` field list omits `agentic_detected_untested` required by §6.1/§8
**Features/Dimension:** 07-scoring · scoring (internal; also cross-checked against 09)

**Description:** The authoritative `ScoreResult` dataclass enumeration in `07-scoring/plan.md §2.2` (line 147) lists `{web_score, agentic_score, overall_score, overall_grade, penalty_raw, coverage_partial, version}` and omits `agentic_detected_untested: bool`. Three other sections of the same plan require that flag as a `ScoreResult` attribute: §6.1 code (line 264), §6.1 prose (line 277, with type), and the §8 test table (line 337, asserts `agentic_detected_untested is True`). §2.2 already includes other non-persisted downstream fields (`coverage_partial`, `version`), so the omission is a genuine internal contradiction — building `ScoreResult` from §2.2 fails the §8 test and cannot satisfy the §6.1 badge contract. (`09-reporting` is unaffected: it derives the badge from `scan.agentic_status == "detected_not_tested"`, never the flag.)

**Evidence:**
- ✗ `07-scoring/plan.md:147` — `ScoreResult ... penalty_raw: int, coverage_partial: bool, version: str` (no `agentic_detected_untested`)
- `07-scoring/plan.md:264/277/337` — flag required as a `ScoreResult` attribute and asserted in tests

**Recommended fix:** **§2.2 is the canonical shape — add the field.** Add `agentic_detected_untested: bool` to the §2.2 field list (preferred per §6.1's intent to distinguish cases "sin re-mirar agentic_status"). Alternatively drop the redundant flag and derive the badge from `agentic_status` as 09/13 do.

### M6 — `07-scoring`: enum-keyed weight dicts indexed by string Finding fields raise KeyError
**Features/Dimension:** 07-scoring · scoring (plan-vs-code-convention; internal + cross-check 06)

**Description:** `07-scoring/plan.md §2.1` declares the weight tables keyed by enum members (`SEVERITY_PENALTY: dict[FindingSeverity, int]` with `FindingSeverity.CRITICAL` etc.) and §2.2/§3 `_penalty_raw` indexes them as `SEVERITY_PENALTY[f.severity]` / `CONFIDENCE_FACTOR[f.confidence]`. But per `06-data-model/spec.md §5.1` (reaffirmed in 06/plan §2.1), `Finding.severity`/`.confidence` are plain `Literal` **strings**, not enum members. Given the repo's `BaseEnum` (`__hash__ = hash(self.value)`, default identity `__eq__`), indexing an enum-keyed dict with the raw value string raises `KeyError` (hash collides, `__eq__` is False — empirically reproduced). The plan specifies no coercion, so the formula as written crashes.

**Evidence:**
- `06-data-model/spec.md §5.1` — `severity: Literal["critical","high","medium","low","info"]`, `confidence: Literal["alta","media","baja"]`
- ✗ `07-scoring/plan.md §2.1` — `SEVERITY_PENALTY: dict[FindingSeverity, int] = { FindingSeverity.CRITICAL: 40, ... }`; `base_enum.py` — `__hash__(self): return hash(self.value)`

**Recommended fix:** **Reconcile inside the 07 plan.** Either key the dicts by the literal `.value` strings, or coerce at the boundary (`SEVERITY_PENALTY[FindingSeverity(f.severity)]`) inside `_penalty_raw`. The §8 table-driven test suite would surface the `KeyError` on first run.

### M7 — `02-attack-levels`: `scans_wiring` "(mismo patrón)" points at dead, signature-incompatible `event_bus.py`
**Features/Dimension:** 02-attack-levels · code-reference (internal)

**Description:** Plan §9 step 7(e) (`backend-attack-levels.md:571-574`) tells the implementer to wire `scans_wiring` into **both** `bus_builder.py` AND `common/infrastructure/event_bus.py` as "mismo patrón". They are not the same pattern: `build_async_bus()` calls wirings **with** args (`auth_wiring(domain, bus)`), matching the real `def X_wiring(domain, bus)` signatures, whereas `init_bus_event()` calls them **without** args (`auth_wiring()`), which is already incompatible and would `TypeError` if invoked. `init_bus_event` has zero callers — it is orphaned dead code; the only live wiring path is `bus_builder.py` (used by `config/tasks.py` worker + `dependencies/common.py` API).

**Evidence:**
- `bus_builder.py` — `auth_wiring(domain, bus)`; wiring defs — `def users_wiring(domain: DomainContext, bus: BusContext)`
- ✗ `event_bus.py:7-11` — `init_bus_event(): auth_wiring()  messaging_wiring()  ...` (no args)
- ✗ `backend-attack-levels.md §9 step 7(e)` — "… y en … event_bus.py (mismo patrón)"

**Recommended fix:** **`bus_builder.py` is the live, correct path.** Drop the `event_bus.py` half of step 7(e) (and ideally delete the orphaned `event_bus.py`); keep only the `bus_builder.py` wiring with the `(domain, bus)` signature. (Reported at both low and medium across two checks; consolidated as medium per the dead-code/misleading-instruction weight.)

### M8 — `12-api`: `domain_error_handler` output misdescribed in plan §5.1
**Features/Dimension:** 12-api · code-reference (internal; same root as H4)

**Description:** `12-api/plan.md §5.1` (line 278) states `domain_error_handler` serializes any `DomainError` to `{ "error": { "code", "message", "details" } }` and that this is "ya resuelto por el fundamento — no se crea nada nuevo." The actual handler emits `{ "errors": [{"code","message"}], "validation": null }` (+ `timestamp`): a plural `errors` array, no `details` key (`ErrorItem` has only `code`+`message`; per-error context uses a fixed whitelist `missing/openFields/holder`, not generic `details`). An implementer wiring client parsing to `response.error.details` breaks.

**Evidence:**
- ✗ `12-api/plan.md:278` — `{ "error": { "code", "message", "details" } }`
- `error_handlers.py` — `ErrorFeedback(errors=[ErrorItem(code, message)], validation=None)`; `api_json.py:24` — appends `timestamp`

**Recommended fix:** Correct §5.1 to the foundation's actual `{ errors: [{code, message}], validation, timestamp }` shape. (Same authoritative resolution as **H4**; this is the internal-code-reference facet of that defect.)

### M9 — `12-api`: `Page[T]`/`encode_cursor` already exist; `CursorPage` duplicates them
**Features/Dimension:** 12-api · code-reference (internal; same root as H5)

**Description:** Three confirmed code-reference checks (`pagination.py` helper, `domain/entities/common/pagination.py`, and the proposed `common/presentation/pagination.py`) all corroborate that `12-api §5.2`'s "no cursor helper in common" claim is false and that the proposed `CursorPage[T]` duplicates the existing `Page[T]` (`next_cursor`, `items`, `apply_presenter`, `to_dict → {next_cursor, items}`). The genuine gap is only a composite `(severity, id)` cursor for findings ordering, which `PageIndex`'s `datetime|uuid` form does not cover.

**Evidence:**
- `common/domain/entities/common/pagination.py` — `Page[T]` + `PageIndex` (base64 `value|uuid`) + `Pagination`
- `common/application/helpers/pagination.py` — `encode_cursor`/`decode_cursor`
- ✗ `12-api/plan.md §5.2` — `CursorPage[T] ... net-new`

**Recommended fix:** Reuse `Page[T]` + the existing codec; extend the encoder for the findings composite cursor only. (Same authoritative resolution as **H5**; consolidated here as the code-reference facet.)

---

## Low severity

### Internal — `01-legal-ethics`

### L1 — `common/legal/` vs `common/domain/legal/` package path inconsistency
**Features/Dimension:** 01-legal-ethics · self-inconsistency (internal)

**Description:** The net-new legal package is given two paths within one file. Intro (line 16), the §2 header (line 56: literal `backend/src/common/legal/`), and the build sequence (lines 189-190) use bare `common/legal`, while the directory-tree code block uses the DDD-correct `backend/src/common/domain/legal/` (line 62) and `common/domain/services/attestation_gate.py` (line 70). The `domain/` path is authoritative (explicit tree + matches the codebase convention cited at lines 38-39 + CLAUDE.md layering).

**Evidence:** `plan.md:56` — `## 2. ... — backend/src/common/legal/` vs `plan.md:62` — `backend/src/common/domain/legal/`

**Recommended fix:** Rewrite lines 16, 56, 189-190 to `common/domain/legal`. (Invariant tests key off symbols, not paths, so no behavioral impact.)

### L2 — `ScanLevel` member casing: 02 uses UPPERCASE, owner 06 uses lowercase
**Features/Dimension:** 01-legal-ethics, 02-attack-levels, 06-data-model · cross-feature-naming (internal)

**Description:** `02-attack-levels` references `ScanLevel.BASICO/.INTERMEDIO/.AVANZADO` (UPPERCASE) at 5 sites, but the owner `06-data-model/plan.md:93` defines `class ScanLevel(BaseEnum): basico | intermedio | avanzado` (lowercase, matching the DDL), and `01` correctly uses `ScanLevel.basico`. Python enum access is case-sensitive → `ScanLevel.BASICO` raises `AttributeError` at module load against the owner's enum.

**Evidence:** `02-attack-levels/backend-attack-levels.md:256` — `(False, ScanLevel.BASICO): _BASIC_NON_GOV` vs `06-data-model/plan.md:93` — `class ScanLevel(BaseEnum): basico | intermedio | avanzado`

**Recommended fix:** **06 is the enum owner (lowercase).** Change 02's `ScanLevel.*` references to lowercase.

### Internal — `02-attack-levels`

### L3 — `command/` (singular) vs `commands/` (plural) handler directory split
**Features/Dimension:** 02-attack-levels · convention (internal; pre-existing repo inconsistency)

**Description:** The new scans module places `ScanHandler` in `application/command/` (singular, mirroring `tenants/`) but `ScanCommand` in `application/commands/` (plural, mirroring `common/`). The §5 comment's `application/command(s)/` notation is fuzzy: only `tenants` uses singular `command/`; `users`/`messaging`/`common` use plural `commands/`. Cosmetic only — imports resolve by exact path.

**Evidence:** `tenants/application/command/` (singular) vs `users/application/commands/`, `messaging/application/commands/` (plural)

**Recommended fix:** Standardize on plural `commands/` (matches `tasks_mapping`'s existing imports) for both `ScanCommand` and `ScanHandler`; tighten the §5 comment.

### L4 — `02`: WhatWeb/Wappalyzer and sitemap collapses are silently un-annotated
**Features/Dimension:** 02-attack-levels · spec-plan-omission (internal)

**Description:** The plan collapses spec-offered tool alternatives to one canonical tool but annotates only some. `Wappalyzer`: spec lists "WhatWeb / Wappalyzer" alternatives; the `ToolId` enum keeps `WHATWEB` only, with no comment (whereas the parallel ffuf/gobuster collapse IS annotated). `sitemap`: spec lists "robots/sitemap" recon; the plan covers robots via `RobotsPolicy` but has no sitemap `ToolId`/invocation — only the sitemap half is truly dropped. Documentation-completeness gaps, not behavioral contradictions.

**Evidence:** spec §3.1 — `Fingerprint: WhatWeb / Wappalyzer`, `Recon: robots/sitemap`; plan `ToolId` has `WHATWEB`/`SUBFINDER`/`DNSX`, no `WAPPALYZER`/`SITEMAP`

**Recommended fix:** Add a one-line comment in each spot mirroring the gobuster annotation.

### Internal — `04-scanning-engine`

### L5 — `run_tool` hardcodes ZAP's `/zap/wrk` container mount for all heavy tools
**Features/Dimension:** 04-scanning-engine · spec-plan-inconsistency (internal)

**Description:** Plan §3.2 hardcodes the DooD container-side mount target to `/zap/wrk` (a ZAP-image convention) for ALL heavy siblings, yet asserts `run_tool()` is the single tool-agnostic helper whose `-v` handling is "uniforme para toda invocación pesada". The other DooD tool (hexstrike) does not use `/zap/wrk`, so its evidence would not land in the host scan dir. Low impact: `ENABLE_HEXSTRIKE=False` on the demo path, so only ZAP runs DooD and the literal is correct.

**Evidence:** `plan.md:208` — `"-v", f"{host_shared_dir}:/zap/wrk", spec.image, *spec.cmd]` (ToolSpec has no container-mount field)

**Recommended fix:** Make the in-container mount target a per-tool `ToolSpec` field (alongside `image`/`cmd`/`memory`).

### L6 — `04`: `CancelToken.is_set` is async but called without `await` in `run_tool`
**Features/Dimension:** 04-scanning-engine · spec-plan-inconsistency (internal)

**Description:** §4.3 defines `async def is_set(self) -> bool:` (Redis GET), but §3.2's `run_tool` rule calls it synchronously: `if cancel.is_set(): return ToolResult(ok=False, coverage_note="cancelado")`. Taken literally, the guard tests an always-truthy coroutine object → `run_tool` early-returns "cancelado" for every tool. Pseudocode in a pending plan; a type-checker would catch the un-awaited coroutine.

**Evidence:** `plan §4.3` — `async def is_set(self) -> bool:  # GET scan:{id}:cancel`; `plan §3.2` — `if cancel.is_set(): ...` (no await)

**Recommended fix:** Add `await`: `if await cancel.is_set():`.

### Internal — `05-agent-team`

### L7 — `ANTHROPIC_API_KEY` listed as net-new but already exists in settings
**Features/Dimension:** 05-agent-team · inaccurate-code-claim (internal)

**Description:** `plan.md:82-84` lists `ANTHROPIC_API_KEY` among keys "se añaden" to `settings.py`, but it already exists at `settings.py:101` (EXTRACTION/OCR/LLM section). The other four keys (`OPUS_MODEL_ID`, `SONNET_MODEL_ID`, `SCAN_BUDGET_S`, `OPUS_SUMMARY_MAX_TOKENS`) are genuinely net-new. Harmless: at worst a no-op re-add.

**Evidence:** `backend/src/common/settings.py:101` — `ANTHROPIC_API_KEY: str | None = None` (pre-existing)

**Recommended fix:** Reference `ANTHROPIC_API_KEY` as reused; add only the four net-new keys.

### Internal — `06-data-model`

> The `AgenticType` delimiter mismatch (data-model) is reported under **M1**; the low-severity duplicate of the same finding is folded there.

### Internal — `07-scoring`

### L8 — Stale `§9.x` cross-references throughout 07 (local spec is `§1`–`§7`)
**Features/Dimension:** 07-scoring · broken-cross-reference (internal)

**Description:** `07-scoring/plan.md` cites the local `./spec.md` (numbered §1–§7) using legacy `§9.x` numbers inherited from the pre-migration monolithic spec. Affected: hyperlinks at lines 18/173/202/228/254/286 and text cites at lines 118/127/134/193/241/247/274/391. Mapping: §9.2→§2, §9.3→§3, §9.4→§4 (+leaderboard in §6), §9.5→§5, §9.7→§7. `spec.md:96`'s self-ref `§9.4 ... autoridad de orden` should read `§6`. Navigational only — normative content is correct.

**Evidence:** `plan.md:202` — `[spec §9.4](./spec.md)`; local `spec.md` headers are `## 1.`–`## 7.` (no §9)

**Recommended fix:** Renumber the `§9.x` refs to the local `§N` per the mapping above; fix `spec.md:96` to `§6`. (Two confirmed checks; consolidated.)

### Internal — `08-ranking-watchlists`

### L9 — `previous_completed_scan` / "COMPLETED" matches no `ScanStatus` value
**Features/Dimension:** 08-ranking-watchlists, 06-data-model · naming-vs-enum-ambiguity (internal)

**Description:** §4.3 names the repo method `previous_completed_scan` ("último scan COMPLETED previo"), but `ScanStatus` has no `completed` value — terminal-success is `done` (`queued|running|partial|done|failed|cancelled`). No literal `status='completed'` filter is ever emitted, so it is a naming/under-specification nit. The real gap: §4.3 defines the comparison base as "tenga grado escrito", and a `partial` scan also terminates with a grade (capped to C), so the base must include both `done` and `partial` — but the predicate is unspecified and "completed" reads as `done` only.

**Evidence:** `08 plan §4.3` — `previous_completed_scan(... )  # último scan COMPLETED previo`; `06 spec:35` — `status ENUM(queued,running,partial,done,failed,cancelled)`

**Recommended fix:** Pin the predicate explicitly to `status IN ('done','partial')` (or "terminal scan with `overall_grade NOT NULL`").

### Internal — `09-reporting`

### L10 — `403/410` error path for `/r/[token]` has no `403` case
**Features/Dimension:** 09-reporting, 12-api · inconsistency (internal)

**Description:** Spec §3 (line 60) and §5.2 (line 103), plus plan line 385 (toast copy), say "errores 403/410" for the public-link path, but §5.1 defines only 404 (nonexistent) and 410 Gone (expired/revoked) — no 403. `12-api` explicitly forbids 403 here ("404, NUNCA 403"). Confined to non-load-bearing toast copy; would yield a dead 403 toast branch.

**Evidence:** `spec §5.1` — `expires_at < now() o revoked_at → 410 Gone`; `spec §5.2` — `errores 403/410 ... vía toast`; `12-api spec:156` — `404 (no 403)`

**Recommended fix:** Change "403/410" → "404/410" in spec §3, §5.2, and plan line 385.

### L11 — Spec §3 says `recharts` "ya presente"; it is not installed
**Features/Dimension:** 09-reporting · spec-vs-plan-contradiction (internal)

**Description:** Spec §3 (line 59) states the gauge uses `recharts (^3.6.0, ya presente)`, but `recharts` is absent from `frontend/package.json`. The plan §0/§2.2 correctly states it is to be installed and openly "corrige la afirmación de la spec §3". Both converge on the same target state; only the spec parenthetical is stale.

**Evidence:** `spec §3` — `recharts (^3.6.0, ya presente)`; `package.json` has no recharts; `plan §0` — "es una dependencia a INSTALAR ... corrige la spec §3"

**Recommended fix:** Change the spec §3 parenthetical to "a instalar (ownership 13)".

### Internal — `10-realtime-live-view`

### L12 — Spec §4 says native `EventSource`; transport is fetch-based `subscribeSSE`
**Features/Dimension:** 10-realtime-live-view, 13-frontend · spec-plan/code-divergence (internal + cross-feature, consolidated)

**Description:** `10 spec §4` (line 88) and `13 §F1/§F6` sketch the client as `new EventSource(url, {withCredentials:true})` with `Last-Event-ID` resume, but the actual transport (`10 plan §4.3-§6.2`; `frontend/src/infrastructure/http/sse.ts`) is the fetch-based `subscribeSSE` with `credentials: "same-origin"` and `?since_seq=` as the effective reconnection cursor. The plan explicitly reconciles this and `resolve_cursor` accepts both cursor sources, so no contradictory behavior — only a risk that a reader codes from the spec in isolation and reaches for native `EventSource`.

**Evidence:** `10 spec:88` — `new EventSource(url, { withCredentials: true })`; `sse.ts:108` — `credentials: "same-origin"`; `10 plan §6.2` — "subscribeSSE usa fetch (no EventSource nativo)"

**Recommended fix:** **`10` plan is authoritative on transport.** Update `10 spec §4` and `13 §F1/§F6` to name `subscribeSSE`/`useScanStream` with `?since_seq=lastSeq` as the effective cursor; keep `Last-Event-ID` only as a compatibility note.

### Internal — `11-auth-magic-link`

### L13 — `SendEmailCommand` attributed to `send_email.py` (which defines the handler)
**Features/Dimension:** 11-auth-magic-link · wrong-code-reference (internal)

**Description:** §0 (lines 47-49) attaches `(SendEmailCommand, despachado por command_bus)` to `src/messaging/application/commands/send_email.py`, but that file defines `SendEmailHandler` and imports the command; `SendEmailCommand` is defined at `common/application/commands/common.py:9`. Cosmetic — the dispatch guidance (§3.1 step 5, §6) is path-agnostic and correct, and the true location is the first import inside the cited file.

**Evidence:** `send_email.py` — `class SendEmailHandler`; `grep 'class SendEmailCommand'` → only `common/application/commands/common.py:9`

**Recommended fix:** Cite the handler at `messaging/.../send_email.py` and the command class at `common/application/commands/common.py` separately.

### L14 — Magic-link email template described as flat `magic_link.html`, not a directory
**Features/Dimension:** 11-auth-magic-link · wrong-code-reference (internal)

**Description:** §2.1 (line 145) and §8 (line 418) describe the new template as a flat file `templates/email/magic_link.html`, but the messaging convention (`smtp_email.py:43-51`) resolves `template_name` to a **directory** `src/messaging/templates/email/<name>/` holding `message.html`/`message.txt`/`subject.txt` (as for `reset_password`/`invitation`). Two issues: the path omits `src/messaging/`, and a flat file would never be loaded (→ runtime `TemplateNotFound`). Mitigated: §3.1 step 5 already uses the correct `template_name="magic_link"`, and the plan repeatedly says "mirror reset_password" (a directory).

**Evidence:** `plan.md:145` — `templates/email/magic_link.html`; actual — `src/messaging/templates/email/reset_password/` (directory with message.html/message.txt/subject.txt)

**Recommended fix:** Change lines 145/418 to reference a `magic_link/` directory with `message.html`, `message.txt`, `subject.txt`.

### Internal — `12-api`

### L15 — `ApiJSONResponse` already special-cases `Page`, emitting a different pagination envelope
**Features/Dimension:** 12-api · code-reference (internal latent gap)

**Description:** `ApiJSONResponse.render()` (`api_json.py:14-20`) already special-cases `isinstance(content, Page)` and emits `{data, pagination:{nextCursor,limit}, timestamp}`, whereas `12-api §5.2` + `test_findings.py` specify a flat `{items, nextCursor}` contract. Returning a `Page` through `ApiJSONResponse` produces the wrong shape; the plan never flags that `ApiJSONResponse` overrides the shape for `Page`-typed content. (Latent gap, not an in-document contradiction.)

**Evidence:** `api_json.py:14-20` — `Page` → `{data, pagination, timestamp}`; `12-api §5.2`/`test_findings.py` — `{items, nextCursor}`

**Recommended fix:** State explicitly whether `CursorPage` bypasses `ApiJSONResponse`'s `Page` wrapping, or adopt the existing `{data, pagination}` envelope as the real contract. (Related to **H5**/**M9**.)

### Cross-feature — low

### L16 — Partial-coverage / cap-C badge predicate (D4) unresolved and inconsistent
**Features/Dimension:** 07-scoring, 09-reporting, 06-data-model, 13-frontend · scoring (cross-feature)

**Description:** `09`'s D4 (the cap-C / "cobertura parcial" badge predicate) is explicitly open and prefers Option B (a persisted `coverage_capped` flag "que 07 persista"), but `07` (authority) derives the label from `scans.status='partial'` and persists only 5 score columns — `ScoreResult.coverage_partial` is transient, never a column; `06` persists no such flag. Meanwhile `13`/`08` already use Option A (`status=='partial'`). Field name also drifts: `coverage_partial` vs `coverage_capped` vs `status=='partial'`. The fallback Option A is already the de-facto contract.

**Evidence:** `07 plan:215` — label from `scans.status='partial'`; `09 plan:467-471` — "Opción B ... coverage_capped que 07-scoring persista. Preferible B"; `06 plan:185` — no `coverage_*` column

**Recommended fix:** **Close D4 in `07`'s favor (Option A).** Predicate is `scans.status=='partial'` (06 persists it as a first-class status). Do not add `coverage_capped`; update `09` D4 to mark Option A chosen and compute `meta.coveragePartial` from `scan.status`. (Note `09:470` argues A≠B semantically, so close it explicitly rather than as a rename.)

### L17 — `product/spec.md` subspec index for feature 06 omits tables 06 defines
**Features/Dimension:** 06-data-model, product/spec.md · index-status-meta (cross-feature)

**Description:** The `product/spec.md:112` subspec-index "Qué cubre" cell for feature 06 lists `(sites, scans, findings, agentic_surface, scan_events, watchlist, magic_tokens)`, omitting `alerts`, `notification_prefs`, and `public_reports` which 06 defines with full DDL (§3.6, §3.8). Also 06's own §1 intro (line 12) omits `notification_prefs`. Cosmetic index/intro-gloss staleness; the authoritative §3 schema is complete.

**Evidence:** `product/spec.md:112` — `(sites, scans, findings, agentic_surface, scan_events, watchlist, magic_tokens)` vs `06-data-model/spec.md:167` — `### 3.6 watchlist, alerts y notification_prefs`, `:182` — `### 3.8 public_reports`

**Recommended fix:** Add `alerts`, `notification_prefs`, `public_reports` to the `spec.md:112` row; add `notification_prefs` to 06's §1 intro.

### L18 — `02-attack-levels/plan.md` lacks the project-wide YAML status frontmatter
**Features/Dimension:** 02-attack-levels · index-status-meta (cross-feature/convention)

**Description:** `02-attack-levels/plan.md` is the only numbered `plan.md` (of 13) without YAML frontmatter; it conveys status via a 1-row table (`🔴 pendiente | 0%`) linking to `backend-attack-levels.md`. All 12 siblings open with `---` frontmatter (`status: pending`, `coverage: 0`, `audited: 2026-06-20`, …). No status contradiction (the table agrees), so this is pure metadata-format drift; the only downside is frontmatter-keyed tooling skipping this file.

**Evidence:** `02-attack-levels/plan.md` top — `# attack-levels — plans` + table, no `---`; siblings (e.g. `03`/`04`) begin with `status: pending\ncoverage: 0`

**Recommended fix:** Add the standard YAML frontmatter to `02-attack-levels/plan.md` (keep the doc-status table as a body element if desired).

> **Additional consolidated low findings** (reported, verified, folded into the entries above to avoid duplication): the second `01` `common/legal` path code-ref (→ **L1**); the second `02` `command/commands` code-ref (→ **L3**); the second `07` `§9.x` cross-ref (→ **L8**); the second `10`/`13` `EventSource` cross-ref (→ **L12**); the second `05` `ANTHROPIC_API_KEY` code-ref (→ **L7**); the second `11` `SendEmailCommand` code-ref (→ **L13**); the second `07` `agentic_detected_untested` cross-check (→ **M5**).

---

## Verified clean

The following had **no confirmed issues** in this audit:

- **Per-feature status metadata:** All 13 features carry consistent `status: pending` / `coverage: 0` frontmatter (with the single **format** exception of `02-attack-levels/plan.md`, L18 — the status value itself is consistent). No status/numbering contradictions.
- **Code-reference accuracy (overwhelmingly clean):** The SaaS-foundation code references are accurate across the board — SAQ worker (`config/tasks.py`), command/handler bus pattern (`buses/commands.py`, `bus_builder.py`, `command_solver.py`, `saq_command_enqueuer.py`), rate limiter + dependency factory, JWT/magic-token services, email/webhook helpers, DB mixins + Alembic single-head migration, settings, and the entire `frontend/` BFF/proxy/i18n/UI-component catalog. Net-new (`src/scans`, `src/sites`) paths are correctly marked as not-yet-existing.
- **Features with no internal contradictions found beyond cross-feature shared issues:** the bulk of `03`, `04`, `06`, `09`, `10`, `11`, `12`, `13` internal logic is self-consistent; their issues are concentrated in the shared seams above (gov-passive tags, AgenticType, error envelope, cursor pagination, static URL, summary column).
- **Cross-dimensions with no confirmed defects:** `auth`/`tenants`/SaaS-foundation modules (out of pentest scope, faithfully described); the `AgenticStatus` enum (consistent underscores across 03/06/07/13); the realtime SSE replay/seq contract (`streaming.py` accurately described, including the `id:`-field gap correctly scoped as not-yet-done); the scoring formula/grade-band normative content (correct despite the stale `§9.x` pointers).

---

## Cross-cutting recommendations

1. **Finish the gov-passive Nuclei migration (H1, M3).** One coordinated edit to `01-plan:108-109` and `04-plan:263` closes the highest-risk defect and unblocks the legal passive-profile test suite.
2. **Make `06-data-model` add the two missing columns (H2 `scans.summary`, M3a `scan_events.progress`)** so the hour-0 schema freeze is complete before the worker/reporting features build against it.
3. **Reconcile the `12-api` contract docs to the real foundation (H4, H5, M8, M9, L15):** error envelope is `{errors:[{code,message}], validation, timestamp}`; cursor pagination reuses `Page[T]`/`encode_cursor`. These four findings share two root code-truths.
4. **Standardize `AgenticType` on underscores in 06's spec (M1)** — one fix resolves every data-model/index-status duplicate.
5. **Fix the static evidence URL prefix to `/data/scans` in `04` (H3).**
