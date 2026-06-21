# Mock / Fixture Audit — Owliver

_Generated audit: are mocks/fixtures still served instead of real data & real calls?_
_Method: 9 area investigators + adversarial verifiers (44 agents). Each suspected mock was re-checked for whether it actually executes in a normal production path._

## TL;DR

- **Backend — clean.** No mock/stub/fixture data is served to users. Scanners really shell out (subprocess/Docker), the agentic prompt-injection lane really drives Playwright + a real LLM judge, scoring/repos/DB are real. The `mock_*`/`fake_*` files are test-only DI and are **not** wired into the live API path.
- **Frontend — this is where mocks remain.** One **always-on** mock plus a **pervasive silent fixture-fallback** baked into every Owliver BFF route and server loader.

---

## 🔴 Frontend — must fix

### 1. Scan history page is 100% fake (unconditional, no backend call at all)
- `frontend/src/application/owliver/server/scan-history.ts:24` — `loadScanHistory()` returns `{ items: scanHistoryFixture, fromFixture: true }` with **no** `backendGet` call. Comment: _"Backend not wired yet."_
- Consumed by `frontend/src/app/(public)/(owliver)/scans/page.tsx:27` → every signed-in user's run history is the 10 fabricated rows in `fixtures/scan-history.ts:143-316`.
- **Fix:** wire `loadScanHistory()` to the real `GET /scans` (history) endpoint via `backendGet`.

### 2. Silent fixture fallback in every BFF route (fires on ANY backend error, no env gate)
These call the **real** backend first (`backendGet`/`backendPost` → `serverHttp` + `X-Api-Key` + Bearer cookie) and return real data on success — but on any non-whitelisted failure they **silently** return fixtures wrapped in a 200/201 success envelope. `bff.ts:69-80` turns a thrown/unreachable backend into `{ ok:false, status:500 }`, which none of the routes' explicit status guards catch, so control falls through to the fixture. **A down backend is indistinguishable from a working one** — dangerous for a security product (fake grades / fake findings / fake "scan created").

| Route | Line | Fixture served on failure |
|---|---|---|
| `api/owliver/scans/route.ts` (POST create) | :33 | demo scan id `scan-fabrikam-demo-0001`, HTTP 201 |
| `api/owliver/scans/[id]/route.ts` (GET detail) | :26 | Fabrikam demo scan (grade E) |
| `api/owliver/scans/[id]/findings/route.ts` | :30 | demo findings list |
| `api/owliver/ranking/route.ts` (public homepage) | :36 | ~40 hardcoded ranking rows |
| `api/r/[token]/route.ts` (public share report) | :30 | demo public report |
| `api/owliver/me/alerts/route.ts` | :19 | static alert prefs (medium) |
| `api/owliver/watchlist/route.ts` | :19 | 4 hardcoded ACME rows (medium) |

> Note: the same real-first-then-fixture pattern also exists in `sites/[id]/route.ts:25`, `scans/[id]/stream/route.ts`, `server/ranking.ts:38`, `lib/report-data.ts:33`, and the `scans/[id]` / `sites/[id]` page shells. Verifiers classed these as "fallback only" (fire on error, not happy path) — same risk, lower confidence they're hit in normal operation. The whole family should be treated together.

**Recommended fix:** make the fallback explicit and opt-in. Either (a) propagate the real error (5xx → error envelope) so failures are visible, or (b) gate every fixture fallback behind an explicit `process.env.OWLIVER_USE_FIXTURES === "1"` dev flag, so production never silently serves demo data.

---

## 🟢 Backend — real (no action needed)

- **Agentic lane** (`worker/agentic/probe.py`, `bridge.py`, `judge.py`, `llm_judge.py`, `payloads.py`, `detector.py`): real headless Chromium via Playwright, real target navigation behind the SSRF/egress guard, real payloads from `data/payloads.json`, real LLM judge + deterministic canary regex.
- **Scanning engine** (`scanning/runner.py`, `registry.py`, `resolver.py`, `health.py`; `run_scan_handler.py`): `run_tool` genuinely shells out (subprocess / DooD Docker dispatch). No dry-run / stub / fixture short-circuit.
- **mock/fake-named files** (`mock_bus_singleton.py`, `mock_domain_singleton.py`, `fake_command_bus.py`, `context_builder.py`, `resend_email.py`): test/DI plumbing only. The live API builds the real domain context (`dependencies/common.py` → `build_async_domain` real SQL repos) and real bus — `AppContextBuilder`/Mock singletons are **not** on the request path.

### Architectural note (not a mock, but worth knowing)
- `backend/src/scans/application/commands/run_scan_handler.py:108-119` never passes `run_team` to `WorkerFlow`, so `WorkerFlow.run_team` is always `None` and `_execute()` always takes the **deterministic** branch. That means the **Agno LLM Team is dead code in production** — `team.py` / `members.py` (`build_team`, `team_prompt`, `build_owasp_agent`, `build_agentic_agent`) are never invoked by any live path. The deterministic tool pipeline (the real one) runs instead. Decide whether to wire the Team in or remove it.
