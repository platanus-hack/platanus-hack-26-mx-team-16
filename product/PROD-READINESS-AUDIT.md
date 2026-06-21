# Production-Readiness Audit — scan-engine & contract fixes

Adversarial multi-agent review (6 reviewers + verification pass) of every fix made
across this session. **32 findings; 7 high/critical; 6 verified real.**

## Verdict

The fixes are **functionally correct and verified in dev** (scans run end-to-end,
ZAP/testssl/nuclei/etc. work on reachable targets, the live theater renders real
data). They are **NOT yet production-safe** without the items below. None cause
silent data corruption, but several (a) only reach prod after a CI rebuild +
redeploy + manual warm step, (b) silently weaken the *advanced* scan, or (c) are
ineffective/abusable behind the prod proxy. Priorities:

---

## P0 — must address before/at deploy

### 1. Deps & toolchain only reach prod via a CI rebuild + redeploy (+ template warm)
- The agno/openai deps, the `uv.lock`, and the `Dockerfile.scanners` apt additions
  (hexdump/`procps`/`gawk`/`xxd`/perl-modules/`dirb`) live in the **prebuilt**
  `ghcr.io/xiberty/owliver-worker-prod` image. CI **does** rebuild it
  (`.github/workflows/build_backend.yml`, `release.yml` → "Build and push worker
  image" from `Dockerfile.scanners`), **but only after these changes are committed,
  pushed, CI runs, and a redeploy/promote happens.** Until then prod runs the stale
  image and testssl/nikto/ffuf/nuclei/agno are all still broken there.
- **nuclei templates:** live runs use `-duc` (no auto-download), so the
  `nuclei_templates` volume **must be pre-warmed**. `warm_scanners.sh` is a manual
  `just warm-scanners` step, **not wired into deploy**, and its defaults
  (`backend_nuclei_templates` volume + a local-built image) don't match the prod
  project name (`owliver-backend-prod_nuclei_templates`) or prod image. → prod
  nuclei finds **0 templates**.
- **ZAP image:** `zaproxy/zap-stable:2.15.0` must already be present on the prod
  host (DooD `docker run` has no pull window inside the tool timeout).
- **Action:** commit + push, confirm CI rebuild+redeploy, parameterize
  `warm_scanners.sh` for prod (volume name + worker image) and run it on deploy,
  and pre-pull the ZAP image on prod hosts.

### 2. ZAP report `report.json` collision + stale-read (correctness bug introduced here)
`backend/src/scans/worker/tools/owasp.py` + `registry.py`
- Every **advanced** scan runs **both** `ZAP_BASELINE` and `ZAP_FULL_ACTIVE`; both
  write `-J report.json` into the **same** `host_shared_dir` → the second
  **overwrites** the first.
- `_zap_result_from_report` trusts **file presence**: it ignores `result.returncode`,
  `stderr`, and `timed_out`, and the report is never cleared between runs. So a
  failed/timed-out ZAP run can read a **stale/previous** `report.json` and report a
  bogus `ok` result with wrong findings.
- **Fix:** per-tool report name (`-J zap_baseline.json` / `-J zap_full_active.json`)
  read back by tool; keep `ok=False` when `timed_out`; delete/`exist_ok`-guard the
  file before each run.

### 3. Anonymous rate-limit collapses to one global bucket behind the prod proxy
`backend/src/scans/presentation/endpoints/enqueue_scan.py`
- Prod uvicorn runs with no `--forwarded-allow-ips`/ProxyHeaders, so
  `request.client.host` is the **proxy IP** for every anonymous request → all
  anonymous `/scan` submissions share one bucket (`scans:ip:<proxy-ip>`): the public
  scan page is globally capped at **5/h for the whole internet** (self-inflicted DoS)
  and gives **zero per-attacker** protection.
- **Fix:** enable `--forwarded-allow-ips=<proxy-cidr>` (or ProxyHeadersMiddleware) and
  key on the right-most untrusted XFF hop, behind a trusted-proxy allowlist. (Same raw
  `client.host` pattern already exists in `dependencies/rate_limit.py:75`.)

---

## P1 — should address

### 4. Anonymous non-gov scan auto-published as PUBLIC (policy/privacy)
`backend/src/scans/application/use_cases/enqueue_scan.py:86` — my override forces
**every** anonymous passive scan to `PUBLIC`, not just gov. Anyone can scan a third
party's site and the findings become world-readable by UUID with **no owner able to
revoke** (`requested_by=NULL`). Spec intent is "`.gob.mx` is the only automatic
public surface." **Decision needed:** scope the auto-public override to `is_gov`
hosts only (and give non-gov anonymous a signed/one-time access link), or accept the
broader exposure.

### 5. nuclei `-fuzzing-templates` stripped → advanced DAST silently disabled
`backend/src/scanning/runner.py` `_DECLARATIVE_FLAGS`. The whitelist wires
`-fuzzing-templates` as part of the spec-§6 guaranteed advanced battery; stripping it
means advanced nuclei runs only default templates (no fuzzing), with **no coverage
note** — A–F scores overstate depth. *(Note: the pinned nuclei 3.3.5 empirically
rejects `-fuzzing-templates` with exit 2, which is why it was stripped to avoid a
hard failure — but the correct fix is to translate it to the valid v3 flag (`-dast`)
so fuzzing actually runs, or emit a visible coverage note, not to silently drop it.)*
`--single-param` (sqlmap) is similar but only broadens scope, not weakens.

### 6. LLM no-key gate checks the wrong provider key
`backend/src/scans/worker/summary.py:154` gates on `settings.ANTHROPIC_API_KEY` while
prod uses `MODEL_PROVIDER=minimax`. It works **only** because a placeholder
`ANTHROPIC_API_KEY` is set; clearing that placeholder silently disables the LLM
summary even though MiniMax is configured. **Fix:** resolve the gate key from the
active provider (`ModelFactory().api_key`).

### 7. Anonymous user can launch an intrusive ACTIVE scan → orphan
Active levels gate only on the client `authorized` boolean, not on auth. An anonymous
`avanzado` scan runs intrusively against any host with **no account trail**, and is
then unreadable/uncancellable/unshareable (`requested_by=NULL`). **Fix:** require auth
for `intermedio/avanzado`.

---

## P2 — hardening / nice-to-have

- **`chmod 0o777`** on every scan dir (`evidence.py`) is world-writable on the shared
  prod host — needed for the uid-1000 ZAP sibling, but consider `0o770` + a shared
  gid, or a fixed uid, instead.
- **Log data-leak:** `run_tool.nonzero_exit` logs up to 500 chars of raw scanner
  stdout/stderr (target URLs w/ query strings, possibly injected secrets) — consider
  redaction.
- **Unbounded reads:** the whole ZAP `report.json` is slurped into `ToolResult.stdout`;
  the LLM prose narrative is stored verbatim — cap both. (Stored-XSS via narrative is
  **not** exploitable — React/JSX auto-escapes.)
- **Exact pins** `agno==2.6.18` / `openai==2.43.0` get no transitive security patches
  without a manual bump (acceptable for reproducibility; track CVEs).
- **`/tmp/owliver-scans`** (local base compose only) is subject to tmp-reaping; prod
  uses `/data/scans` so this is dev-only.
- **Orphaned `scan_data` named volume** left in base compose `volumes:` — harmless,
  remove for clarity.

---

## What's solid (verified, no action)
- IDOR not introduced — `require_scan_access`/`require_scan_owner` correctly gate
  PUBLIC-by-UUID vs PRIVATE-404 vs owner-only mutations.
- `_to_host_path` is a verified **no-op in prod/dev** (`/data/scans:/data/scans`,
  `SCAN_DATA_HOST_DIR` unset) — backward-compatible.
- PROCESS_LABEL fix persisted across all 3 compose files.
- SSE snake_case (`scan_id`/`web_score`) correctly mirrors the raw `events.py` wire.
- testssl `--warnings batch`, ZAP `-J` round-trip, ffuf/katana flag mapping, and the
  new `run_tool` logging are correct.
