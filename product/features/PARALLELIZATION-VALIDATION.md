---
status: reference
title: Validación cruzada del plan de paralelización (specs + planes + código)
generated_by: workflow parallelization-cross-validation-v2 (28 agentes — 9 contratos + 13 plan×código + 5 supuestos + síntesis)
date: 2026-06-20
validates: ./PARALLELIZATION.md
---

# Validación cruzada del plan de paralelización

> Resultado de validar [`PARALLELIZATION.md`](./PARALLELIZATION.md) en tres frentes:
> **(A)** consistencia spec×spec de los 9 contratos congelados, **(B)** los 13
> `plan.md` (CÓMO) contra el código real vía codegraph, y **(C)** los supuestos
> globales del plan contra `backend/` y `frontend/`. Regla de reconciliación:
> **el código gana** sobre cualquier supuesto de spec/plan.
> **TL;DR:** el esqueleto del plan (olas, camino crítico `06→04→05→03`, Day-1
> `06/02`) se sostiene; hay 5 contratos a reconciliar antes de congelar y
> 0 colisiones greenfield (los 13 features siguen sin construir).

## Veredicto general

El plan de paralelización **se sostiene**: la estructura de olas (W1→W5), el camino crítico `06→04→05→03` y el set Day-1 (`06, 02`) son correctos contra las specs, los planes y el código real. Confirmado con alta confianza que los 13 features numerados están sin construir (solo existe el boilerplate SaaS) y que ningún path/tabla del motor de pentest colisiona. **El único riesgo alto** que puede forzar retrabajo es la **contradicción de wiring de tools entre 02 (pre-filtra `tools=` vía `resolve_toolset`) y 05 (entrega TODAS las tools al LLM y deja que elija por nivel)**: rompe la invariante legal "el agente literalmente no recibe tools activas en el camino gov/automático" (01 §2.2) y debe resolverse antes de construir W3/W4. Todo lo demás son alineaciones de documentación o secuenciaciones intra-ola, no rupturas de paralelización.

---

## A. Validación cruzada entre specs (contratos congelados)

| Contrato | Productor lo define | Consistencia | Mismatch más grave | ¿Afecta paralelización? |
|---|---|---|---|---|
| Finding/AgenticResult + enums + scan_events + DDL (06) | sí | minor-mismatch | `prompt-input` (spec, guion) vs `prompt_input` (plan, underscore); `type` es `str` libre, no `Literal` | No |
| ScanLevel + TOOLSET_WHITELIST + `resolve_toolset` (02/04) | sí | **contradiction** | 02 pre-filtra `tools=`; 05 da todas las tools al LLM → invariante legal no estructuralmente forzada | **Sí** |
| common/legal (invariante legal/ético) (01) | sí | minor-mismatch | `GOV_PASSIVE_PROFILE` discrepa consigo mismo en tags Nuclei; RobotsPolicy no aparece en 04 | No |
| runner API `run_tool`/`ToolResult`/`resolve_tools` (04↔05) | sí | minor-mismatch | 05 usa `run_subprocess(...).raw`+timeout inline vs `run_tool(...).stdout`; solo pseudocódigo | No |
| scoring + orden leaderboard (07) | sí | minor-mismatch | `penalty_raw` persistido = solo web; 08/13 no lo explicitan | No |
| SSE scan_events + replay-then-tail (10) | sí | consistent | campo `agent` es `str` no-enum; etiquetas de carril podrían driftear | No |
| Cookie de sesión + dependency (Google boilerplate) | sí | minor-mismatch | label dice `current_user/optional_current_user`; símbolo real es `get_session_user/SessionUserDep` | No |
| REST wire-shape + error envelope (12) | sí | minor-mismatch | 13-spec omite `PATCH /watchlist/{id}` pero pide "Switch monitor"; wrapper `{data}` solo en planes | No |
| subagent interface + crawl-result (05/03/04) | partial | minor-mismatch | crawl-result `{DOM, network[]}` nunca congelado; firma `run_tool` diverge spec(04)↔plan(05) | **Sí** |

**Contratos con contradicción / mismatch med-high a corregir:**

- **A1 — 02 vs 05, tool-wiring (HIGH, bloqueante).** 02 plan §5 construye `owasp_agent(tools=[TOOL_FUNCTIONS[ti.tool] for ti in resolve_toolset(...)])` — filtra por `(is_gov, level)` *antes* de que el agente exista. 05 §1.1 hardcodea lista estática completa y le dice al LLM "Decide SOLO qué tools correr según el `{level}`". Ambos comparten el cuerpo de `ScanHandler` (02 §11 lo marca como ítem abierto). **Decidir un solo dueño del modelo de enforcement antes de W3/W4**; si gana 05, el `resolve_toolset` de 02 queda como código muerto y la invariante legal deja de estar estructuralmente forzada. **Arreglar en 05 (alinear a `tools=` pre-filtrado) o documentar la decisión en 02 §11.**

- **A2 — crawl-result nunca congelado (MED).** Ningún spec (03/04/05) congela la forma `{DOM snapshot, network[]}` que produce `crawl_site` y consume el fingerprint de 03. Mitigado porque `06→04→05→03` los serializa, pero genera churn en los costuras 04→05 y 05→03. **Congelar un tipo `CrawlResult` (dueño: 03 o 05) antes de W4.**

- **A3 — firma `run_tool` diverge spec(04) vs plan(05) (MED).** 04 §3.2 congela `run_tool(image, cmd, shared_dir)`; 05 plan §0/§2 asume `run_tool(spec, *, target, host_shared_dir, cancel) -> ToolResult`. Los wrappers de 05 están escritos contra la firma del plan. **04 debe exponer exactamente la firma con `ToolResult`/`cancel`/`TOOL_SPECS` o 05 rompe al importar.** Reconciliar antes de W3/W4.

- **A4 — `-duc` en flags Nuclei (MED).** 02 congela el tuple `_BASIC_GOV` SIN `-duc` (lo declara mecánica de 04); 04 §7 exige `-duc` en cada run. Los flags congelados de `resolve_toolset` no son los flags ejecutados. Cosmético si se trata como mecánica de ejecución, pero **conviene que 02 documente que los flags son lógicos, no literales.**

- **A5 — tags Nuclei del perfil pasivo discrepan dentro de 01 (MED).** 01 spec §3 lista `exposures,misconfiguration,ssl,tech,dns`; 01 plan §2.4 congela `("ssl","tech","http-misconfig")`. 04 importa `GOV_PASSIVE_PROFILE` como fuente de verdad pero no enumera. **El productor (01) debe fijar una sola lista canónica antes de que 04 construya `resolve_tools()`.**

- **A6 — `penalty_raw` web-only no propagado (MED).** 07 plan §6.2/§10.4 decide que la columna persistida = penalty del **web** solamente; 08 §2.1 y 13 §F4 lo consumen sin saber que es web-only. No bloquea (el `ORDER BY` es idéntico) pero **08/13 deben documentar la semántica web-only.**

- **A7 — `PATCH /watchlist/{id}` omitido en 13-spec (MED).** 13 spec §F3/§F11 lista solo GET/POST/DELETE pero pide un "Switch monitor" que requiere ese PATCH; el 13-plan §2.2/§4 lo restaura. **Editar 13-spec para añadir el PATCH** (consistencia interna del consumidor).

**Contratos limpios** (consistent / minor cosmético, no afectan paralelización): scoring (07), SSE envelope (10), cookie de sesión (Google boilerplate) y el grueso del wire-shape REST (12). Todos los consumidores referencian los mismos nombres de campo y valores de enum; los deltas son naming (`get_session_user` vs label) o under-specification resuelta en los planes.

---

## B. Validación de planes de implementación vs código

| Feature | Plan vs realidad | Refs a código OK? | Colisiones greenfield | Deps ocultas que muevan olas |
|---|---|---|---|---|
| 01-legal-ethics | accurate | sí | ninguna | suite de invariantes cruza W2/W3 (01 no completable dentro de W2) |
| 02-attack-levels | accurate | sí | ninguna | 06 es **hard blocker intra-W1**; ScanHandler runnable depende de 05 (W4) |
| 03-agentic-surface | accurate | sí | ninguna | `tools/agentic.py` co-reclamado por 05 y 03 (contenidos divergentes) |
| 04-scanning-engine | accurate | sí | ninguna | import duro de 01 (W2) y 06 (W1); ordenado OK |
| 05-agent-team | accurate | sí | ninguna | **`agno`+`anthropic` NO en pyproject — paso de instalación no listado** |
| 06-data-model | accurate | sí | ninguna | — |
| 07-scoring | accurate | sí | ninguna | gating real = contratos hora-0 de 06 (finding.py + enums) |
| 08-ranking-watchlists | accurate | sí | ninguna | **contrato `requested_by IS NULL` que 05 (W4, posterior) debe honrar** |
| 09-reporting | accurate | sí | ninguna | **columna `scans.summary` (¿06 o 05?) y consumos de 13 (W5) — tensión de orden** |
| 10-realtime-live-view | accurate | sí | ninguna | 06 debe exponer `ScanEventRepository` + `next_seq`/cursor-reader |
| 12-api | **mostly-accurate** | en su mayoría | ninguna | enqueuer SAQ no expone key/retries; 01-helpers preceden POST /scans intra-W2 |
| 13-frontend | accurate | sí | ninguna | — (consumos soft contra spec congelada de 12) |

**Hallazgos prominentes:**

- **Colisiones greenfield: NINGUNA.** Los 13 features están sin construir; `src/scans`, `src/sites`, `src/scanning`, `src/common/legal` y todas las tablas de pentest están ausentes. Todos los paths de creación están limpios.

- **Refs a código que NO existe (correctamente marcadas como deps, no errores):** `ScanLevel`/`ScanVisibility` (06), `Finding`/`AgenticResult`/`scan_events` (06), `run_tool`/`resolve_tools`/`CancelToken`/`TOOL_SPECS` (04), `common/legal` helpers (01), `CursorPage` (12), `require_scan_access` (12). Ninguna es un error de plan.

- **Refs a código falsamente justificadas (CODE gana):**
  1. **06 decision #2** — el plan justifica usar PK `uuid` diciendo "presenters mapean uuid→id"; **el código emite la clave `"uuid"`** (`presenters/tenant.py:15`), no `"id"`. La decisión (`uuid`) es correcta por el mixin, pero **la justificación es factualmente falsa** — corregir el racional.
  2. **12 §9.4** — el plan trata `optional_current_user` como "riesgo abierto a coordinar con 11"; **`get_optional_authenticated_user` YA EXISTE** (`session.py:42`). Riesgo sobrestimado — eliminarlo.
  3. **12 §0/línea 71** — el plan dice que `AppContext` carga "sesión, redis"; **el código tiene solo `domain/bus/scheduler`** (`context_builder.py:14-16`). `/ready` y rate-limit deben sacar redis/session de sus propias deps.
  4. **12 §2** — el plan asume `queue.enqueue('run_scan', key=..., retries=..., timeout=...)`; **el `SaqCommandEnqueuer` hardcodea `queue.enqueue("handle_command", timeout=AWS_LAMBDA_MAX_TIMEOUT)`** sin passthrough de key/retries (`saq_command_enqueuer.py:40`). La capa-2 de idempotencia (job-key) requiere extender el enqueuer compartido, o caer solo en el índice único parcial (capa-1).

- **Conflictos plan↔spec (todos resueltos deliberadamente, no abiertos):** 09 y 13 **anulan la spec** que afirma "recharts ya presente" — el código confirma que recharts/sonner/chart.tsx/accordion **NO existen**; el plan tiene razón (son net-new). 13-plan también vuelve moot el paso "añadir vitest" (vitest ya está configurado).

- **Planes derivados/stale:** ninguno está derivado en lo estructural. El único con etiqueta `mostly-accurate` es **12-api** por las 4 imprecisiones de arriba (todas sobre boilerplate SAQ/AppContext/auth), no sobre el wire-shape ni las olas.

- **Deps ocultas que el modelo de olas subestima (NO mueven olas, pero deben anotarse):**
  - **Intra-W1 no es libremente paralelo:** 02 depende de artefactos de 06 (ScanLevel/sites/scans) → 06 debe entregar primero dentro de W1.
  - **Acoplamiento forward 08→05:** 08 (W3) codifica el contrato `requested_by IS NULL = origen cron/seed` que 05 (W4, posterior) debe obedecer al encolar `run_scan`; si no, el encadenado de alertas hace no-op silencioso.
  - **`scans.summary` (09):** 09 (W3) necesita esa columna JSONB; si la posee la migración de 05 (W4), 09 queda soft-blocked por una ola posterior. Asignar dueño (mover a 06/W1 o tratar capa ejecutiva de 09 como soft-blocked en 05).

---

## C. Validación contra el código (supuestos globales)

| Área | Veredicto | Hallazgo clave |
|---|---|---|
| boilerplate-base | confirmed | Exactamente 8 módulos SaaS; auth/current_user/SAQ/tenants/messaging presentes |
| numbered-features-already-built | confirmed | 0 de 13 features construidos; sin código scanner/agno/playwright |
| frontend-base | confirmed | BFF/proxy/HTTP-client/design-tokens listos; cero superficie de pentest |
| module-path-collisions | confirmed | `common/legal` libre; 1 sola migración con 8 tablas SaaS; sin colisión de tablas |
| agno-worker-stack | confirmed | SAQ genérico listo; sin stack Docker de scanners (04 lo debe autorear) |

**Supuesto central "los 13 numerados están pending / solo boilerplate": CONFIRMADO.** `backend/src` contiene exactamente `admin, assets, auth, common, messaging, profile, tenants, users`. `pyproject.toml` no tiene `agno`/`anthropic`/`playwright`/scanners. Una sola migración Alembic (`720929e089fd_initial`) con 8 tablas SaaS. Todos los specs llevan `status: pending`. Frontend sin superficie de pentest.

- **Features ya construidos (total o parcial): NINGUNO** de los 13 numerados.
- **Scaffolding faltante (a autorear, no bloquea olas):** (1) `agno`+`anthropic` en pyproject (dep implícita de 05); (2) topología Docker de worker/scanners dedicada (el worker SAQ actual está co-ubicado en el contenedor de la API vía `saq ... worker_settings & uvicorn`) — 04 la debe crear; (3) `seed/` no existe (08 usa `backend/seed/gob_mx.txt` mientras `command.load` lee de `fixtures/`).
- **Colisiones de path/tabla: NINGUNA.** Advertencia operativa: encadenar migraciones nuevas con Alembic autogenerate desde `720929e089fd` para evitar **multiple-heads** cuando las olas corran en paralelo.

---

## Deltas al plan de paralelización

### MUST fix antes de confiar en el plan
1. **Reconciliar el modelo de enforcement de tools (02 vs 05)** — decidir un solo dueño: o 05 alinea a `tools=` pre-filtrado por `resolve_toolset`, o 02 documenta que cede el modelo y la invariante legal se valida de otro modo. **Bloqueante de la costura W3/W4 y de la invariante 01 §2.2.** (Contrato A1.)
2. **Congelar la firma de `run_tool`** en 04 exactamente como `run_tool(spec, *, target, host_shared_dir, cancel) -> ToolResult` (+`TOOL_SPECS`), o los wrappers de 05 rompen al importar. (Contrato A3.)
3. **Congelar el tipo `CrawlResult` `{DOM, network[]}`** (dueño 03 o 05) antes de W4. (Contrato A2.)
4. **Fijar la lista canónica `nuclei_tags_allow`** en 01 (spec §3 vs plan §2.4) antes de que 04 construya `resolve_tools()`. (Contrato A5.)
5. **Asignar dueño y ola a la columna `scans.summary`** — moverla a la migración de 06 (W1) o declarar la capa ejecutiva de 09 soft-blocked en 05 (W4). (Dep oculta 09.)

### Edges/notas a añadir a PARALLELIZATION.md (estructurales, no mueven olas)
6. **Ordenamiento intra-W1:** añadir edge implícito `06 → 02` — 02 (ScanLevel/sites/scans) no puede compilar su capa backend hasta que 06 entregue sus contratos hora-0. W1 no es libremente paralelo.
7. **Contrato cross-wave 08→05:** registrar `requested_by IS NULL = origen cron/seed` como contrato que 05 (W4) debe implementar, no como detalle interno de 08.
8. **Deliverable de 06 para 10:** explicitar que 06 expone `ScanEventRepository` en `DomainContext` + métodos `next_seq` y cursor-reader (`seq > since_seq ASC`), o `replay.py` de 10 queda bloqueado.
9. **Anotar 02 split:** "pure-logic + tests" en W1; "handler-integration" (resolve_toolset→tools=, hexstrike healthcheck) diferido a la unión con 04/05.

### Nice-to-have (documentación / no bloquea)
10. Añadir paso de build: `agno`+`anthropic` a `pyproject.toml` (05).
11. Corregir 12-api: renombrar a `get_authenticated_user`/`get_optional_authenticated_user`, eliminar riesgo §9.4 (ya existe), corregir claim de `AppContext` (domain/bus/scheduler), y decidir enqueuer extendido vs solo índice único para la capa-2 de idempotencia.
12. Corregir racional de 06 decision #2 (presenters emiten `"uuid"`, no `"id"`).
13. Documentar `penalty_raw` web-only en 08/13 (A6); añadir `PATCH /watchlist/{id}` a 13-spec (A7); documentar flags Nuclei como lógicos no literales en 02 (A4).
14. Reconciliar `seed/` vs `fixtures/` (08/06) y usar Alembic autogenerate encadenado desde `720929e089fd` para evitar multiple-heads en olas paralelas.

**El esqueleto del plan (olas, camino crítico `06→04→05→03`, Day-1 `06/02`) NO requiere cambios.** Todos los deltas son reconciliaciones de contratos antes de congelar, secuenciaciones intra-ola, o correcciones de documentación.

---

## Acciones recomendadas

1. **Resolver A1 (enforcement de tools 02 vs 05)** — es el único riesgo que garantiza retrabajo; decidir dueño antes de arrancar W3/W4.
2. **Congelar las 3 firmas/tipos de costura** antes de W3/W4: `run_tool`/`ToolResult` (A3), `CrawlResult` (A2), y `nuclei_tags_allow` canónico (A5).
3. **Añadir el edge intra-W1 `06 → 02`** y declarar a 06 como entregable hora-0 (finding.py, enums, ScanLevel, ScanEventRepository).
4. **Asignar dueño a `scans.summary`** (preferible 06/W1) y registrar el contrato `requested_by IS NULL` (08→05).
5. **Aplicar las correcciones de 12-api** (nombres de deps, AppContext, enqueuer/idempotencia) y el racional de 06 decision #2 — son ediciones de plan baratas que evitan confusión en implementación.
6. **Antes de codear:** añadir `agno`+`anthropic` a pyproject, planear la topología Docker de scanners (04), y encadenar migraciones con autogenerate desde `720929e089fd`.

---

## Apéndice — hallazgos crudos por agente

### A. Contratos (spec×spec)

| Contrato | Define | Consistencia | Afecta paralelización | Confianza |
|---|---|---|---|---|
| Finding / AgenticResult Pydantic contracts (frozen in finding.py) + their enums (severity, confidence, source, category, agentic_status), the scan_events shape (events.py), and the scan-engine table DDL with its key constraints: UNIQUE(scan_id,seq), UPSERT key (site_id,dedupe_key), and the partial-unique index scans(site_id,level) WHERE status IN ('queued','running'). | yes | minor-mismatch | no | high |
| ScanLevel enum (basico\|intermedio\|avanzado, imported from 06) + the frozen TOOLSET_WHITELIST keyed by (is_gov: bool, level: ScanLevel) -> tuple[ToolInvocation(tool: ToolId, flags)], surfaced through the pure resolver resolve_toolset(is_gov, level, *, demo, hexstrike_ok). 02 owns the policy/content + resolver contract; 04 owns the concrete runtime data structure + enforcement drop point. | yes | contradiction | sí | high |
| common/legal module (legal/ethics invariant) — a pure, layer-free package backend/src/common/domain/legal/ owning the legal invariant primitives: constants SCANNER_USER_AGENT and API_SCAN_RATE_LIMIT; predicates is_active() and default_visibility(); enforce_attestation()/AttestationRequiredError(422); the frozen GOV_PASSIVE_PROFILE + assert_within_passive_profile(); and the RobotsPolicy Protocol (defined here, implemented in 04). Producer = 01-legal-ethics (spec narrative + plan.md concrete signatures). Consumers: 12-api (enforce_attestation gate, default_visibility, API_SCAN_RATE_LIMIT via create_rate_limit_dependency) and 04-scanning-engine (assert_within_passive_profile, SCANNER_USER_AGENT, RobotsPolicy, is_active filtering). | yes | minor-mismatch | no | high |
| scanning-engine runner API: run_tool(spec, *, target, host_shared_dir, cancel: CancelToken) -> ToolResult (fields tool/ok/stdout/stderr/duration_s/timed_out/coverage_note), TOOL_SPECS registry, resolve_tools(*, is_gov, level) -> list[ToolInvocation]. Boundary with 05: tool-functions parse the raw JSON/JSONL string (ToolResult.stdout) into list[Finding] in pure Python inside the function; the engine never parses. | yes | minor-mismatch | no | high |
| "scoring API (dedupe/score) + leaderboard order" — the deterministic Python scoring service that turns deduped Finding[] into web_score/agentic_score/overall_score/overall_grade(A–F)/penalty_raw plus agentic_status (3 states), and the leaderboard order/tiebreak (overall_grade ASC, penalty_raw DESC). Owned by 07-scoring; consumed by 05 (worker invokes it), 08 (leaderboard query), 09 (report render), 13 (UI render). | yes | minor-mismatch | no | high |
| SSE scan_events schema + replay-then-tail: typed event envelope {seq:int, type:enum, agent:str, tool?:str, severity?:str, message:str, ts:datetime, payload?:dict, progress?:int(0-100)} with type ∈ {agent_status,tool_start,tool_end,finding,phase,score,done,error}; seq is the sole monotonic ordering key (per scan); endpoint GET /scans/{id}/stream does replay-from-Postgres (seq>cursor, cursor from Last-Event-ID header or ?since_seq=) then subscribe+tail on Redis channel scan:{id}:events; PG-write-before-Redis-publish; client dedupes seq<=lastSeq; cookie HttpOnly (SameSite=Lax) auth (EventSource withCredentials) or one-shot ?stream_token=; heartbeat ~20s; compression off; cancellation = done with payload.outcome='cancelled' (NOT a separate type). | yes | consistent | no | high |
| Auth session cookie + cookie-based route dependency. The boilerplate Google login (SaaS auth module, already implemented) emits an HttpOnly, SameSite=Lax cookie carrying a JWT, and provides a FastAPI dependency get_session_user(request) -> User (SessionUserDep) that reads the cookie and returns the authenticated User or 401. This same cookie authenticates the SSE live-view stream (EventSource cannot send Authorization headers). Consumers 12-api and 10-realtime consume that cookie for GET /scans/{id}/stream auth and other authenticated endpoints (/auth/me, watchlist, scans). | yes | minor-mismatch | no | high |
| REST wire-shape (OpenAPI) + error envelope: endpoint routes/methods/payloads for scans (idempotent POST), sites, ranking, watchlist, alerts, public reports, health; cursor pagination; SSE stream; and the unified error envelope {error:{code,message,details}}. | yes | minor-mismatch | no | high |
| "agent-team subagent interface + crawl-result": (a) the two Sonnet members of the Agno Team — owasp_agent (name="OWASP Scanner") and agentic_agent (name="Agentic Surface Auditor"), each a Claude("sonnet") Agent that only decides WHICH tools to run per level and accumulates Finding[] into Team session_state (never via response_model); and (b) the crawl-result (DOM snapshot + captured network requests) that the agentic subagent's crawl_site tool produces and the detection/fingerprint logic consumes. | partial | minor-mismatch | sí | high |

### B. Planes (plan.md×código)

| Feature | Accuracy | Colisiones greenfield | Deps ocultas | Confianza |
|---|---|---|---|---|
| 01-legal-ethics | accurate | — | ScanLevel / ScanVisibility enums do not exist in code yet; plan §2.3 depends on 06-data-model defining them (or temporarily hosting them in legal and having 06 re-export). This is the critical hard-dep and the plan acknowledges it (§0, §5 step 1).; enqueue_scan use case + POST /scans + scans table columns (authorized, authorized_at, requested_by, level, visibility) and sites.is_gov are owned by 06-data-model and 12-api; the attestation gate, visibility default, and rate-limit wiring cannot be exercised end-to-end until W1(06)+W2(12) land. Wave plan places 01 in W2 alongside 12 and after 06 in W1 — consistent.; resolve_tools(is_gov, level) and RobotsPolicy impl are owned by 04-scanning-engine (W3); the passive-profile/robots invariant tests (§4 test_passive_profile.py, test_robots.py) therefore cannot go green until W3. Plan §5 sequences this correctly, but means this 'W2' feature's full test suite only passes after W3/W5 features exist — a soft cross-wave dependency the wave model understates (01 is not fully completable within W2). | high |
| 02-attack-levels | accurate | — | 06-data-model is a HARD upstream blocker, not just a same-wave peer: the plan imports ScanLevel from src/common/domain/enums/scans.py AND requires the scans/ and sites/ modules (SiteRepository, sites.is_gov) + the ScanCommand fields — none of which exist yet. The wave plan places 06 and 02 in the same W1, but 02's resolver/whitelist/ScanCommand cannot compile until 06 ships ScanLevel + sites/scans entities. This is an intra-wave ordering dependency the W1 grouping understates.; 05-agent-team is implied for the ScanHandler body to be functional: build_owasp_agent, TOOL_FUNCTIONS (ToolId→run_* mapping), and orchestrator.run(url, level) are all owned by 05 (W4). The plan scopes 02 to only the resolve_toolset call site + tools= filter, but the ScanHandler it stands up in W1 references 05-owned symbols that won't exist until W4 — so a runnable ScanHandler can't land until W4. The wave plan (02 in W1, 05 in W4) understates this code-level coupling on the shared ScanHandler.; 04-scanning-engine owns the frozen whitelist data structure, worker enforcement/drop-point, hexstrike healthcheck (ENABLE_HEXSTRIKE semantics) and run_tool execution. 02's resolver consumes the hexstrike_ok boolean and the inject-by-constructor healthcheck cache that 04 populates at worker startup. 04 is W3 — so 02's hexstrike path is non-functional until W3, another cross-wave coupling. | high |
| 03-agentic-surface | accurate | — | 03 hard-depends on 05 producing runtime symbols (agentic_agent, ModelFactory, ScanEventEmitter, session_state['agentic'] convention, the closure wrapper pattern) — not just data contracts. The wave plan places 05 and 03 together in W4, but the critical path 06->04->05->03 implies 05 must land its worker scaffolding (models.py/events.py/team wiring) BEFORE 03's tools/agentic.py can integrate. Within-wave ordering 05-before-03 is real, slightly understated by 'W4={05,03}'.; 03 depends on 04 delivering Playwright(Python)+Chromium in Dockerfile.scanners and assert_public_target+demo allow-list and CancelToken — listed as W3. Correctly upstream of W4. No miss.; Shared-file coordination: tools/agentic.py is co-claimed by 05 and 03 with divergent contents; needs an owner decision (03 owns the agentic tool internals; 05 owns wiring it into members.py). Wave plan does not flag this co-ownership. | high |
| 04-scanning-engine | accurate | — | Plan depends on 01-legal-ethics (common/legal: constants, assert_within_passive_profile, RobotsPolicy Protocol) as a DIRECT import in runner.py/resolver.py/robots.py. The wave plan places 04 in W3 and 01 in W2 (earlier), so this is satisfied ordering-wise, but it is a hard import-level dep, stronger than a soft contract — the engine's signatures literally import from 01.; Plan depends on 06-data-model ScanLevel enum for resolve_tools() signature and Finding/coverage/evidence shapes — 06 in W1 (before W3), correctly ordered. Hard build-time blocker per plan §9 ('06 bloquea el resto').; Plan §3.5/§3.6 depend on 02-attack-levels providing the (is_gov, level) whitelist TABLE that resolve_tools materializes; 02 is in W1, before 04 in W3 — satisfied. Wave plan lists 02 as day-1, consistent.; Plan §4.1/§6 implies 08-ranking-watchlists owns the gob.mx seed/fixtures and AUTOMATIC_ALLOWED_LEVELS scheduler guard; 08 is a same-wave (W3) SIBLING, not a predecessor. The scheduler service in §2.1 reuses the scanners image but its guard logic is cross-feature within the same wave — a mild coordination point, not understated as a hard dep (plan correctly marks it 'lo posee 08'). | high |
| 05-agent-team | accurate | — | MISSING RUNTIME DEPENDENCY: the entire feature is built on the Agno Team framework (Team mode='coordinate', Agent, RunContext, agno.run) plus a Claude model client, but 'agno' and any Anthropic SDK ('anthropic') are NOT in backend/pyproject.toml dependencies (verified — only fastapi/saq/redis/sqlalchemy/etc). Adding agno + anthropic to pyproject is an un-stated prerequisite step the plan's build sequence (§8) never lists. This is an implicit dep of THIS feature on a new package install, not on a numbered feature.; 02-attack-levels (W1) is consumed only transitively via 04's resolve_tools(is_gov, level); the wave plan places 02 in W1 and 05 in W4, so this is satisfied — but the plan understates that the per-level tool whitelist (02) must be wired INTO 04's resolve_tools before 05 can rely on 'the subagent only receives permitted tools' as defense-in-depth.; 10-realtime-live-view (W3) — plan's ScanEventEmitter publishes to Redis channel 'scan:{id}:events' and the ScanEvent type enum is owned by 06; the SSE/replay consumer side is 10. Wave plan has 10 in W3 (before 05 in W4) so ordering is fine, but the emit-side event-type enum contract is a shared 06/10 dependency the plan leans on. | high |
| 06-data-model | accurate | — | — | high |
| 07-scoring | accurate | — | 07-scoring hard-depends on 06-data-model for the Finding/AgenticResult Pydantic contracts (src/scans/domain/contracts/finding.py) AND the enums/scans.py module — the scoring service literally imports both. The wave plan places 06 in W1 and 07 in W2, which is consistent (07 after 06). No understatement here, but worth flagging that 07 is effectively unbuildable until 06's hour-0 frozen contracts (finding.py + enums/scans.py) land — these are the gating artifact, not all of 06.; Soft/runtime deps on 04-scanning-engine (coverage jsonb shape → partial_coverage) and 03/05 (agentic_status). The plan correctly isolates these via primitives (boolean + enum) so the pure domain service compiles and tests without 03/04/05. These are W3/W4 but only the worker WIRING (step §9.4, 'enganche en el worker' in 05) needs them — the scoring module + its test suite (the feature's core, coverage>0) ship with only 06's contracts present. Wave plan does not understate this; the dependency is genuinely deferrable to the integration step. | high |
| 08-ranking-watchlists | accurate | — | 08 depends hard on 12-api (W2) beyond just exposing endpoints: the net-new CursorPage[T] pagination helper (§3.3) and the leaderboard filter live in 12; ranking pagination cannot ship without 12. Wave plan puts 12 in W2 (before 08's W3), so ordering holds, but the dependency is structural, not just 'endpoints'.; 08's monitoring contract REQUIRES 05-agent-team (W4) to honor 'requested_by=user_id for manual, NULL for cron/seed' when it enqueues run_scan. 05 is a LATER wave than 08 (W4 vs W3), so 08 codifies a contract that a downstream-wave feature must obey — a forward/circular coupling the wave plan understates. EvaluateSiteAlerts chaining 'at end of scan' also depends on 05/04 invoking it.; 08 depends on 01-legal-ethics (W2) for AutomaticActiveScanError + AUTOMATIC_ALLOWED_LEVELS and on 02-attack-levels (W1) for ScanLevel.basico — the cron's legal guard (§4.2) is inert without both. These are in earlier waves, so satisfiable, but the guard is a hard compile/runtime dep, not optional.; 08 depends on 07-scoring (W2) having already written overall_grade/penalty_raw/partial-cap and on 04-scanning-engine for visibility/dedupe_key/first_seen. Plan is explicit it 'never recalculates', so a 07/04 schema slip silently breaks ranking order and alert dedup. | high |
| 09-reporting | accurate | — | 06-data-model: feature depends on a net-new scans.summary JSONB column AND on FindingRecord exposing status/first_seen/last_seen (the presenter is typed against the persisted record, not the frozen Finding contract). Plan flags this as D1 and a BLOCKING risk, but the wave plan (W1=06, W3=09) only models a coarse 06->09 dependency and understates that 09 needs a SPECIFIC schema addition (summary column) that may instead be owned by 05's migration — a 09<-05 coupling the waves miss (05 is in W4, AFTER 09 in W3).; 05-agent-team: presenter reads scans.summary = serialized ExecutiveSummary from synthesize_summary (05 §6). 05 is in W4 but 09 is in W3 — if the summary column/persistence is owned by 05, 09 cannot fully render the executive layer until 05 lands. Wave ordering (09 before 05) understates this; plan's D1 calls it a blocker.; 07-scoring: badge 'cobertura parcial' needs a coverage-cap signal (D4: scan.status=='partial' vs a coverage_capped flag 07 must persist). Predicate is unresolved and depends on 07's schema choice. 07 is in W2 (before 09) so ordering is fine, but the exact column contract is an open cross-feature dependency.; 03-agentic-surface: the 'star finding' canary evidence shape and redaction of the prompt-injection payload depend on 03's evidence format. 03 is in W4 (after 09 in W3); the public-redaction test ('exploit never in DOM') can't be fully exercised against real agentic evidence until 03 lands.; 12-api: the four endpoints (GET /scans/{id}, /report.pdf, POST /share, GET /r/{token} with 404/410) and use cases GetScan/GetScanReportPdf/CreatePublicShare/GetPublicReport are owned by 12 (W2, before 09 — ordering OK). 09 only supplies presenter bodies + PDF render, correctly scoped.; 13-frontend: installs (recharts, chart.tsx, accordion, sonner) + (public) root layout + A–F color tokens are owned by 13 (W5, AFTER 09 in W3). 09 frontend components consume artifacts that, per waves, don't exist until two waves later — a real ordering tension the wave plan understates (though plan scopes 09 to 'define data contract, not install'). | high |
| 10-realtime-live-view | accurate | — | Plan needs 06-data-model to expose ScanEventRepository ON DomainContext (so endpoint reads app_context.domain.scan_event_repository) AND to declare two extra repo capabilities beyond the documented append: seq reservation (next_seq) and a cursor reader (seq > since_seq ASC, replay/list_since). Wave plan puts 06 in W1 and 10 in W3 so the ordering holds, but these two specific repo methods are an explicit ask the plan itself raises as 'to confirm with 06' — if 06 ships only append, 10's replay.py is blocked.; Endpoint body depends on require_scan_access + cookie-based current_user from 12-api (W2) — correctly upstream of 10 (W3). No miss.; stream_token EMISSION (endpoint or field on GET /scans/{id}) is owned by 12-api; 10 only provides mint/consume. A latent cross-feature seam but plan is explicit about it.; ScanEventEmitter lives in src/scans/worker/events.py and is INSTANTIATED by 05-agent-team (W4) — which is DOWNSTREAM of 10 (W3). 10 only fixes the emitter contract/file; the worker flow that closes a single emitter per scan (guaranteeing monotonic seq) is 05's job. The wave plan's critical path (06->04->05) covers this, but the seq-monotonicity invariant is a real 10<-05 contract coupling worth noting. | high |
| 12-api | mostly-accurate | — | Hard dep on 01-legal-ethics is concrete-code-level, not just W2-sibling: EnqueueScan.execute() calls resolve_host_flags, enforce_attestation, default_visibility from common/legal and API_SCAN_RATE_LIMIT — none exist. Wave plan puts 01 and 12 in the same wave (W2) with no intra-wave ordering, but 12's POST /scans cannot compile/run without 01's legal helpers first.; SAQ job-key idempotency (layer 2, plan §2) depends on extending the shared SaqCommandEnqueuer/command bus to pass key/retries/timeout — this is a change to common boilerplate not owned by 06/12 and not surfaced as a dependency anywhere in the wave plan.; 10-realtime-live-view: plan delegates /scans/{id}/stream body AND the stream-token/cookie auth hook to 10; 12 only declares the route. Wave plan has 10 in W3 (after 12 in W2), so the stream endpoint stays a stub until W3 — acceptable but means 12 ships incomplete re: spec's SSE surface.; 09-reporting: /r/{token} redaction and /report.pdf render owned by 09 (W3). 12 (W2) can only ship owner-check + byte passthrough stubs until 09 lands. | high |
| 13-frontend | accurate | — | — | high |

### C. Supuestos globales (×código)

| Área | Veredicto | Ya implementado | Colisiones | Confianza |
|---|---|---|---|---|
| boilerplate-base | confirmed | auth module (login, logout, refresh, google login, password reset) — /Users/vic/Projects/experiments/owliver/backend/src/auth/; current_user dependency (get_authenticated_user + AuthenticatedUserDep/AuthenticatedSuperuserDep) — /Users/vic/Projects/experiments/owliver/backend/src/common/infrastructure/dependencies/session.py; SAQ background-job mechanism (Queue, handle_command worker, SaqCommandEnqueuer, async_tasks_mapping, run_async dispatch + example endpoint) — config/tasks.py + src/common/infrastructure/buses/saq_command_enqueuer.py; tenants module with roles/invitations/permissions — /Users/vic/Projects/experiments/owliver/backend/src/tenants/ + src/common/database/models/tenants/; users + profile modules — src/users/, src/profile/; messaging/email primitive (EmailService + SmtpEmailService + SendEmail command + templates) — src/messaging/; assets module (disk + S3 storage) — src/assets/; admin module (set_user_password, enqueue_example_job) — src/admin/ | None of the 13 numbered pentest features are implemented as backend modules: src/scans, src/findings, src/agentic_surface, src/watchlist, src/alerts, src/public_reports, src/scan_events, src/worker are all ABSENT — no path collisions for new pentest modules.; Note: an SQSCommandEnqueuer exists alongside SaqCommandEnqueuer but is a stubbed/commented-out alternative; SAQ is the active path. Not a collision, just an unused alternate. | high |
| numbered-features-already-built | confirmed | SaaS boilerplate only: auth (login, logout, refresh, google-login, password reset), users, profile, tenants (roles, invitations, members, api-keys), common (buses, SAQ command enqueuer, SSE infra, permissions), messaging, assets (s3/disk storage), admin (set password, enqueue example job); Generic SAQ (Redis) async-job mechanism with AsyncTaskResolver and a reference ExampleJobCommand — the substrate features 04/05 will build the pentest worker on, but no pentest jobs registered; Generic SSE/event-publisher infrastructure under common/infrastructure/sse and domain/events — substrate for feature 10 realtime-live-view, but no scan-event channels; Frontend SaaS shell: dashboard, settings, roles, api-keys, profile, members pages + BFF auth routes under app/api/auth | ninguna | high |
| frontend-base | confirmed | Auth BFF routes (login/logout/refresh/reset-password/invitations) at src/app/api/auth/**/route.ts; HTTP client layer: serverHttp, localHttp, authHttp with auth-header + dedup-refresh interceptors (src/infrastructure/http/client.ts); Edge proxy with X-Api-Key injection, CF-Access support, auth redirects and refresh-loop breaker (src/proxy.ts); Canonical login flow page.tsx -> /api/auth/login -> serverHttp -> backend with HttpOnly cookies; Protected + public Next.js route groups with dashboard/members/roles/settings/profile/api-keys and register/reset/invitations pages; Full design-token system in globals.css (teal primary, 0.75rem radius, Figtree+Geist Mono, light+dark, 78 oklch tokens) matching DESIGN.md | ninguna | high |
| module-path-collisions | confirmed | SaaS boilerplate backend modules only: admin, assets, auth, common, messaging, profile, tenants, users (backend/src); Single initial Alembic migration with 8 boilerplate tables: users, tenants, tenant_users, tenant_roles, tenant_user_invitations, tenant_api_keys, email_addresses, phone_numbers; common/infrastructure/services/rate_limiter.py (and jwt_token_service, callback_code, redis_token_store) — reused by 01/11 per plan | ninguna | high |
| agno-worker-stack | confirmed | Generic SAQ (Redis-backed) async job queue: queue + handle_command dispatch in backend/config/tasks.py; SaqCommandEnqueuer (run_async dispatch) + MetaCommand serialization in backend/src/common/infrastructure/buses/; async_tasks_mapping registry pattern (tasks_mapping.py) for binding enqueued commands to bus handlers; Worker startup/shutdown lifecycle (DB session_maker + Redis client in ctx); Canonical example background job (ExampleJobCommand + enqueue_example_job endpoint) to copy for new jobs; Worker launch wiring in docker/start-dev, docker/commands, docker-compose.debug.yml | ninguna | high |
