---
feature: agent-team
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §1–§6; 04-scanning-engine/plan.md §3.2/§9; 06-data-model/plan.md §2.2/§2.4; 07-scoring §1–§6; 03-agentic-surface §; 02-attack-levels §; config/tasks.py; common/application/data/tasks_mapping.py
---

# Owliver — Equipo de agentes Agno + worker — plan de implementación (CÓMO)

> La spec de esta feature define **el cerebro**: un Agno `Team` en modo
> `coordinate` (orquestador Opus + 2 subagentes Sonnet) donde **las
> tool-functions parsean su salida cruda a `list[Finding]` en Python puro** y el
> LLM solo decide *qué* tools correr. Este plan cablea ese diseño sobre la infra
> que ya existe: el job entra por **SAQ** (`config/tasks.py` → `handle_command`
> → `AsyncTaskResolver` → `command_bus`), un `RunScanHandler` corre el flujo del
> worker, recoge `Finding[]` deterministas vía `session_state`, delega
> dedup+scoring a Python ([07-scoring](../07-scoring/spec.md)) y usa Opus
> **solo** para el resumen ejecutivo con `output_schema`.
>
> Principio operativo: **el LLM nunca está en el camino de datos.** Parsing,
> dedup, scoring y persistencia son Python determinista; el structured-output de
> Opus se reserva al resumen ejecutivo (<2k tokens). Lo único net-new que esta
> feature **posee** es el paquete `src/scans/worker/` (ensamblado del Team,
> tool-functions wrapper, `WorkerFlow`) y el enganche `RunScanCommand` en el
> bus/SAQ.

## 0. Estado y dependencias

Esta feature se monta sobre código que en parte **aún no existe** y en parte ya
está en el repo. Orden real de habilitación en §8. Hoy:

- **Bloquea ⇐ [06-data-model](../06-data-model/spec.md)**: necesita los contratos
  congelados `src/scans/domain/contracts/finding.py` (`Finding`, `AgenticResult`,
  enums `severity/confidence/source/category`) y `events.py` (`ScanEvent`); el
  `ScanORM`/`FindingORM`/`AgenticSurfaceORM`/`ScanEventORM` y sus repos ABC
  (`ScanRepository` enqueue idempotente, `FindingRepository` UPSERT por
  `(site_id, dedupe_key)`, `ScanEventRepository` append `seq` monótono);
  `services/dedupe.compute_dedupe_key`. **El worker NO redefine ninguno** — los
  importa.
- **Bloquea ⇐ [04-scanning-engine](../04-scanning-engine/spec.md)**: necesita
  `src/scanning/` — `run_tool(spec, *, target, host_shared_dir, cancel)
  -> ToolResult` (firma de 04 §3.2), `resolve_tools(is_gov, level)`, el
  `CancelToken`, `TOOL_SPECS` (con `timeout`/`mechanism`/`image`), el watchdog de
  budget global (~8 min) y el guard de egress. **Las tool-functions de esta
  feature NO ejecutan procesos**: llaman a `run_tool()` y parsean
  `ToolResult.stdout`.
- **Delega ⇒ [07-scoring](../07-scoring/spec.md)**: dedup, `web_score`,
  `agentic_score`, `overall_score`, `overall_grade`, `penalty_raw`,
  `agentic_status`. El worker invoca esas funciones puras; no las reimplementa.
- **Consume [03-agentic-surface](../03-agentic-surface/spec.md)**: el subagente
  agéntico (puente de ataque, LLM-juez, canary) y la forma `AgenticResult`.
- **Consume [02-attack-levels](../02-attack-levels/spec.md)** vía 04:
  `resolve_tools` ya aplica la whitelist por nivel; el subagente solo recibe las
  tools permitidas (defensa en profundidad: ni siquiera puede elegir una activa
  contra gov).

Infra **ya existente** que se reutiliza tal cual (verificada en el repo):

- **SAQ**: `backend/config/tasks.py` define `worker_settings`
  (`queue`, `functions=[handle_command]`, `cron_jobs=[]`, `startup`, `shutdown`),
  lanzado con `saq config.tasks.worker_settings`. `startup(ctx)` inyecta
  `ctx["db_config"]` y `ctx["redis"] = Redis.from_url(...)` — **ese mismo
  cliente Redis es el que usan el `CancelToken` (04) y el publish de
  `scan_events`**.
- **Resolución de comandos**: `handle_command` abre sesión DB, construye el bus
  (`build_async_bus`) y delega a `AsyncTaskResolver(command_bus, payload)`, que
  busca el `command_name` en
  `backend/src/common/application/data/tasks_mapping.py` (`async_tasks_mapping`)
  y despacha al handler suscrito en `infrastructure/bus_wiring.py`. **El job de
  pentest se registra exactamente así** (§3).
- **Patrón comando/handler**: `Command` (ABC con `to_dict`/`from_dict`) +
  `CommandHandler[TCommand]` (dataclass con `async execute(command)`); ver
  `src/common/application/commands/common.py` (`ExampleJobCommand`) y
  `src/messaging/application/commands/example_job.py` (`ExampleJobHandler`) como
  plantilla copy-me del job asíncrono end-to-end.
- **Encolado**: `SaqCommandEnqueuer.enqueue(command)` usa
  `command.__class__.__name__` como `command_name`. El `POST /scans` (12) hace
  `command_bus.dispatch(RunScanCommand(...), run_async=True)`.
- **Settings**: `src/common/settings.py` — aquí se añaden las claves de modelos
  (`ANTHROPIC_API_KEY`, `OPUS_MODEL_ID`, `SONNET_MODEL_ID`), `SCAN_BUDGET_S`,
  `OPUS_SUMMARY_MAX_TOKENS`.

## 1. Dónde vive el código — paquete `src/scans/worker/`

El equipo y el flujo del worker son código de esta feature; viven en un
subpaquete del módulo `scans` (06 es dueño del dominio/contratos/repos de
`scans`; el worker es la capa de *aplicación* que los orquesta). Net-new:

```
backend/src/scans/
  application/
    commands/
      run_scan.py            # RunScanCommand (Command) + RunScanHandler (CommandHandler)
  worker/
    flow.py                  # WorkerFlow.run(scan_id, url, level, is_gov) — el coreógrafo
    team.py                  # build_team(deps) -> Team  (orquestador Opus + 2 members Sonnet)
    members.py               # build_owasp_agent(...), build_agentic_agent(...)
    tools/
      owasp.py               # run_nuclei/run_zap/run_testssl/... wrappers → list[Finding]
      agentic.py             # crawl_site/classify_dom_llm/fingerprint_vendors/run_promptfoo/run_garak
      _accumulate.py         # helper: empuja Finding[] a run_context.session_state["findings"]
    parsers/
      nuclei.py              # parse_nuclei(stdout) -> list[Finding]   (P prioritario)
      testssl.py             # parse_testssl(stdout) -> list[Finding]  (P prioritario)
      security_headers.py    # parse_security_headers(stdout) -> list[Finding] (P prioritario)
      zap.py                 # parse_zap_baseline(stdout) -> list[Finding] (4º)
      generic.py             # best-effort para nikto/sqlmap (1 Finding genérico, sev media)
      owasp_map.py           # DICT estático template-id/cwe/probe → A01..A10 / LLM01..LLM10
    summary.py               # ExecutiveSummary (BaseModel) + synthesize_summary(...) con Opus
    events.py                # ScanEventEmitter — seq monótono + publish Redis + append repo
    models.py                # ModelFactory (Claude opus/sonnet) leyendo settings
```

> **Por qué bajo `scans/` y no un `agents/` top-level.** El worker consume los
> repos y contratos de `scans` (06) y persiste `scans`/`findings`/
> `agentic_surface`/`scan_events`. Mantenerlo en `src/scans/worker/` evita un
> import cíclico entre módulos y respeta la Clean Architecture del repo
> (`application` orquesta `domain`; el `RunScanHandler` es un command-handler de
> `application/commands/`, igual que el resto del codebase).

## 2. Las tool-functions wrapper — parser DENTRO de la función

Cada tool del subagente es una **función Python** registrada en el `Agent`. No
ejecuta procesos ni decide nada: llama a `run_tool()` (04), parsea el `stdout`
crudo a `list[Finding]` con el parser determinista (P de 06/07), empuja los
findings al `session_state` compartido y devuelve un **string corto** que el LLM
usa solo para decidir el siguiente paso. **No** devuelve `Finding[]` al LLM (eso
lo re-teclearía/truncaría, §6).

```python
# src/scans/worker/tools/owasp.py  (forma de referencia)
from agno.run import RunContext
from src.scans.domain.contracts import Finding
from src.scanning import run_tool, TOOL_SPECS, CancelToken
from src.scans.worker.parsers.nuclei import parse_nuclei
from src.scans.worker.tools._accumulate import accumulate

def make_run_nuclei(*, target, host_shared_dir, cancel, emit):
    async def run_nuclei(run_context: RunContext) -> str:
        """Ejecuta Nuclei y registra hallazgos OWASP web. Úsalo en todos los niveles."""
        emit.tool_start("nuclei")
        result = await run_tool(TOOL_SPECS["nuclei"], target=target,
                                host_shared_dir=host_shared_dir, cancel=cancel)
        findings = (parse_nuclei(result.stdout) if result.ok
                    else [coverage_meta("nuclei", result.coverage_note)])  # §4
        accumulate(run_context, findings)        # session_state["findings"] += findings
        emit.tool_end("nuclei", ok=result.ok, n=len(findings))
        return f"nuclei: {len(findings)} hallazgos ({'ok' if result.ok else result.coverage_note})"
    return run_nuclei
```

- Las tools se construyen con un **closure** (`make_run_*`) que captura
  `target`, `host_shared_dir`, `cancel` (CancelToken de 04) y el `emit`
  (`ScanEventEmitter`), porque esos valores son por-scan y no deben venir del
  LLM. El `Agent` recibe la función ya cerrada; el LLM solo la invoca sin args.
- `accumulate(run_context, findings)` escribe en
  `run_context.session_state["findings"]` (estado compartido del Team — Agno lo
  propaga a miembros y persiste; ver §5). Es la **única** vía por la que los
  `Finding` salen de las tools: nunca por `output_schema`/`response_model`.
- El **mapeo a categoría OWASP** (`A01–A10`/`LLM01–LLM10`) vive en
  `parsers/owasp_map.py` como dict/YAML estático curado (template-id/cwe/probe →
  categoría); **nunca** se le pide al LLM.

### 2.1 Parsers priorizados (mismo recorte que la spec §2.2)

| Parser | Entrada (`ToolResult.stdout`) | Dueño/prioridad |
|---|---|---|
| `parse_nuclei` | JSONL (`-jsonl`) — `info.severity`→severity, `classification.cvss-score`→cvss, `cwe`→category | P (alta densidad) |
| `parse_testssl` | JSON (`-oJ`) — TLS/SSL → severity + A02/A05 vía dict | P |
| `parse_security_headers` | JSON con grade — headers ausentes → Finding + A05 | P |
| `parse_zap_baseline` | JSON baseline | 4º |
| `generic` (nikto/sqlmap) | texto best-effort → 1 Finding sev media | best-effort o se corta |

`garak`/`promptfoo` los parsea la familia agéntica ([03](../03-agentic-surface/spec.md));
aquí se exponen como tools del `agentic_agent` con el mismo patrón wrapper.

## 3. Enganche en SAQ — `RunScanCommand` + `RunScanHandler`

Copia exacta del patrón `ExampleJobCommand`/`ExampleJobHandler`:

1. **`RunScanCommand(Command)`** (`src/scans/application/commands/run_scan.py`):
   dataclass con `scan_id: str`, `url: str`, `level: str`, `is_gov: bool`;
   `to_dict`/`from_dict` triviales (todo serializable — sin objetos de dominio en
   el payload, igual que el resto de comandos encolados).
2. **`RunScanHandler(CommandHandler[RunScanCommand])`**: `async execute(command)`
   abre los repos (vía el `domain`/sesión que ya inyecta `handle_command`),
   instancia `WorkerFlow` y llama `await flow.run(...)`. El handler es **fino**:
   toda la coreografía vive en `WorkerFlow`.
3. **Registro** en `src/common/application/data/tasks_mapping.py`:
   `RunScanCommand.__name__: RunScanCommand`.
4. **Suscripción** en el `bus_wiring` del módulo `scans`
   (`src/scans/infrastructure/bus_wiring.py`):
   `bus.command_bus.subscribe(command=RunScanCommand, handler=RunScanHandler(...))`.
   Sin esto, el worker lanza `NotRegisteredCommand` al recoger el job.
5. **Encolado** (lo hace 12 en `POST /scans`):
   `command_bus.dispatch(RunScanCommand(...), run_async=True)` →
   `SaqCommandEnqueuer` → cola Redis → `handle_command` → `AsyncTaskResolver` →
   `RunScanHandler.execute`.

> No se añade un nuevo `function` a `worker_settings`: el pentest reusa
> `handle_command` (un único punto de entrada para todos los jobs), como el resto
> del repo. `cron_jobs` lo toca 08 (scheduler gov), no esta feature.

## 4. Flujo del worker — `WorkerFlow.run(...)` paso a paso

```
WorkerFlow.run(scan_id, url, level, is_gov):
  1. scan.status = running; emit.agent_status("Iniciando escaneo")   # seq=1
  2. cancel = CancelToken(redis, scan_id)            # de 04; chequeado entre tools
     session_state = {"findings": [], "agentic": []}
     team = build_team(target=url, level=level, is_gov=is_gov,
                       cancel=cancel, emit=emit)      # tools ya cerradas (§2)
  3. await team.arun(prompt(url, level),             # Opus coordina; members en paralelo
                     session_state=session_state)    # NO usamos su .content para datos
  4. raw = session_state["findings"]                 # Finding[] deterministas
     deduped = dedupe(raw)                            # 07
     web, agentic_sc, overall, grade, penalty, ag_status = score(deduped, session_state["agentic"])  # 07
  5. summary = await synthesize_summary(compact(deduped, top_n=...))  # Opus, output_schema, <2k tok
  6. persist: ScanRepository.update(scan_id, status=..., scores, grade,
                                    coverage, tools_status);
              FindingRepository.upsert_many(deduped);     # UPSERT (site_id, dedupe_key)
              AgenticSurfaceRepository.save(session_state["agentic"]);
              ScanEventRepository ya recibió cada evento vía emit (append seq)
     emit.score(...); emit.done()                    # último seq
```

Notas normativas del flujo:

- **Fallo parcial (spec §4) — siempre Python, nunca LLM.** Cada tool wrapper
  envuelve `run_tool()` y, si `result.ok is False` (timeout / no-zero /
  excepción / WAF), produce un **Finding-meta** `"tool X no completó"`
  (`severity=info`, `confidence=baja`) y lo acumula, además de marcar
  `scans.coverage[tool]=failed|timeout`. El flujo **CONTINÚA**; nunca se propaga
  la excepción. Como `info=0` no penaliza (07 §2), el meta no infla ni baja el
  score, pero deja rastro de cobertura.
- **Cancelación / budget (delegado a 04).** `CancelToken` se chequea **antes** de
  cada tool (`run_tool` lo hace internamente); el **watchdog de budget global
  ~8 min** (04 §4) aborta las tools restantes y fuerza el cierre del scan aunque
  el LLM siga "pensando". El worker solo respeta el contrato: si `cancel.is_set()`
  o se agotó el budget → cierra con `status=cancelled`/`partial` y persiste lo
  acumulado.
- **`status` final**: `done` si corrieron todos los scanners **base**;
  `partial` si faltó ≥1 scanner base (coverage incompleta); `cancelled` si
  cancel/budget; `failed` solo si un error fuera de tool (DB, ensamblado) rompe
  el flujo — en cuyo caso se persiste `scans.error`.
- **Eventos**: `ScanEventEmitter` mantiene un `seq` monótono por scan, hace
  `append` vía `ScanEventRepository` (persistencia/replay) **y** `publish` al
  canal `scan:{id}:events` (live-view). Tipos:
  `agent_status|tool_start|tool_end|finding|phase|score|done|error`
  (enum de 06). El **detalle** del replay/SSE pertenece a 10-realtime; aquí solo
  se **emiten** los eventos en cada paso.

## 5. Contrato con el coordinador y paralelismo

- **Modo `coordinate`** (Agno): `Team(mode="coordinate", model=Claude(opus),
  members=[owasp_agent, agentic_agent], instructions=...)`. El coordinador Opus
  recibe `{url, level}`, decide a qué miembro(s) delegar y **sintetiza**; pero
  como las tools escriben en `session_state`, su síntesis no toca datos.
  "En paralelo" significa que el **coordinador LLM** dirige el fan-out a los
  miembros (Nota B5 de la spec) — no es un `asyncio.gather` literal nuestro.
- **Estado compartido**: se pasa `session_state={"findings": [], "agentic": []}`
  a `team.arun(...)`; las tools lo mutan vía `run_context.session_state` (API de
  Agno confirmada). Tras `arun`, el worker lee ese mismo dict (no
  `RunOutput.content`). Esto es lo que **saca al LLM del camino de datos**: los
  `Finding` nunca pasan por un mensaje del modelo.
- **Qué recibe cada subagente**:
  - `owasp_agent` (Sonnet, `name="OWASP Scanner"`): tools = wrappers OWASP que
    `resolve_tools(is_gov, level)` (04) habilitó para ese nivel; instrucción
    "decide SOLO qué tools correr según el nivel; NO redactes ni reconstruyas
    findings". Recibe `{url, level}`.
  - `agentic_agent` (Sonnet, `name="Agentic Surface Auditor"`): tools =
    detección + probes agénticos (03); produce el inventario `AgenticResult` +
    findings de probes en `session_state["agentic"]`. Recibe `{url, level}`.
- **Sin `output_schema` en los miembros** (decisión dura, §6): tools +
  structured-output conviven mal en Agno/Claude. Los miembros solo orquestan.

## 6. Por qué Opus solo en síntesis (y cómo se acota)

- **El LLM no parsea** (spec §2): `output_schema=list[Finding]` sobre agentes con
  ~9 tools es zona de bug (Agno #2612/#2433/#2847 — detección incorrecta de
  structured-output en Claude y truncado con muchos findings). Si fallara, el
  escaneo base no produciría `Finding[]` válidos → sin demo. Por eso el parsing
  es Python puro en las tools.
- **Opus solo redacta el resumen ejecutivo** y solo ahí se usa structured-output:
  `summary.py` define `ExecutiveSummary(BaseModel)` (campos: `narrative: str`
  "Owliver te explica", `top_risks: list[TopRisk]` con `title`/`severity`/
  `why_it_matters`) y un `Agent(model=Claude(opus), output_schema=ExecutiveSummary)`.
- **Acotado en tamaño**: `synthesize_summary` recibe un **resumen compacto** —
  top-N por severidad con `title`+`severity`+`category`+`impact`, **sin** el
  `evidence` jsonb. Objetivo `OPUS_SUMMARY_MAX_TOKENS` (<2k). Scoring/dedup ya
  ocurrieron en Python (07): Opus **no** calcula scores ni deduplica.
- **Smoke-test obligatorio antes del demo** (spec §2): verificar que Agno detecta
  el structured-output de Claude para `ExecutiveSummary` — es el único punto donde
  el producto depende de esa ruta.

## 7. Settings y modelos — `models.py`

`ModelFactory` lee `src/common/settings.py` y devuelve `Claude(id=...)`:
`opus()` → `OPUS_MODEL_ID`, `sonnet()` → `SONNET_MODEL_ID`, leyendo
`ANTHROPIC_API_KEY`. Centralizar aquí permite mockear los modelos en tests
(inyectar un fake que no llama a la API) sin tocar `team.py`. `SCAN_BUDGET_S`
(~480) y `OPUS_SUMMARY_MAX_TOKENS` viven también en settings.

## 8. Secuencia de build

1. **06-data-model**: contratos `finding.py`/`events.py`, ORMs y repos ABC,
   `compute_dedupe_key`. (Bloquea todo.)
2. **04-scanning-engine**: `run_tool`/`ToolResult`, `resolve_tools`,
   `CancelToken`, `TOOL_SPECS`, watchdog de budget, egress. (Bloquea las tools.)
3. **07-scoring**: `dedupe`, `score` (web/agentic/overall/grade/penalty/status).
4. **`src/scans/worker/parsers/`**: los 3 priorizados (`nuclei`, `testssl`,
   `security_headers`) + `owasp_map.py` + `zap` (4º) + `generic`. Tests puros
   (§9) sobre fixtures de `stdout` reales recortados.
5. **`src/scans/worker/tools/`** + `_accumulate` + `events.py`: wrappers que
   atan `run_tool` ↔ parser ↔ `session_state` ↔ `emit`.
6. **`team.py` + `members.py` + `models.py`**: ensamblado del Agno Team.
7. **`summary.py`**: `ExecutiveSummary` + `synthesize_summary` (Opus) + smoke-test.
8. **`flow.py` + `run_scan.py`**: `WorkerFlow`, `RunScanCommand`/`RunScanHandler`;
   registro en `tasks_mapping` + `bus_wiring`.
9. **Verde end-to-end**: un scan básico real contra juice-shop produce `Finding[]`
   dentro del budget; un fallo de tool inyectado deja el scan `partial`, no
   `failed`.

Esta feature se considera `implemented`/coverage>0 cuando la suite §9 pasa y el
flujo §4 corre end-to-end sobre un target de prueba.

## 9. Suite de tests — `backend/tests/scans/worker/`

Convención del repo (`tests/<área>/...`, pytest async, `expects`, funciones
standalone, AAA, fixtures por función). Las tools externas y los modelos LLM se
**mockean**: estos tests prueban la **lógica del worker/parsers**, no las
herramientas ni la API de Anthropic.

| Archivo | Capa | Asserts |
|---|---|---|
| `parsers/test_parse_nuclei.py` | puro | JSONL fixture → `Finding[]` con `severity`/`cvss`/`category` (A0x) correctos; `info.severity` desconocida ⇒ `info`; JSONL vacío ⇒ `[]`. |
| `parsers/test_parse_testssl.py` | puro | JSON fixture → severities + A02/A05 vía dict; entrada malformada ⇒ no rompe (devuelve `[]` + log). |
| `parsers/test_parse_security_headers.py` | puro | headers ausentes → `Finding` A05; grade presente mapeado. |
| `parsers/test_owasp_map.py` | puro | template-id/cwe/probe → categoría exacta; id no mapeado ⇒ fallback determinista (no excepción). |
| `tools/test_tool_partial_failure.py` | unit (mock `run_tool`) | `run_tool` devuelve `ok=False`/timeout ⇒ la tool acumula **Finding-meta** (`severity=info`, `confidence=baja`), marca `coverage[tool]=failed/timeout`, **no** lanza, y el flujo de las demás tools sobrevive. |
| `tools/test_tool_accumulates_into_state.py` | unit | la tool empuja `Finding[]` a `run_context.session_state["findings"]` y devuelve un string corto (no los findings). |
| `worker/test_flow_happy_path.py` | integración (Team mockeado) | `WorkerFlow.run` con un Team fake que puebla `session_state` ⇒ llama `dedupe`/`score` (07), persiste `scans`+`findings`, emite eventos con `seq` monótono y termina en `done`. |
| `worker/test_flow_partial_status.py` | integración | con ≥1 scanner base fallido ⇒ `status=partial`, `coverage` refleja el fallo, los findings buenos persisten; **el scan no queda `failed`**. |
| `worker/test_flow_cancel_budget.py` | integración | `cancel.is_set()` / budget agotado ⇒ no arranca la siguiente tool, cierra `cancelled`/`partial`, persiste lo acumulado (no cuelga). |
| `summary/test_executive_summary_smoke.py` | smoke (modelo fake/real-gated) | `synthesize_summary` con `output_schema=ExecutiveSummary` devuelve un objeto válido sobre el resumen compacto; prompt ≤ `OPUS_SUMMARY_MAX_TOKENS`. **Único test que ejerce structured-output de Opus.** |
| `commands/test_run_scan_registration.py` | unit | `RunScanCommand` está en `async_tasks_mapping` y suscrito en `bus_wiring`; `to_dict`/`from_dict` round-trip; payload 100% serializable. |

## 10. Decisiones y riesgos

1. **Tools + `output_schema` (response_model) = zona de bug → parsing en
   Python.** Es la tesis central (spec §2.1): pedir a Sonnet que "devuelva SOLO
   `Finding[]`" con ~9 tools alucina/trunca/pierde `cvss`/`evidence`. Mitigación:
   las tools parsean a `Finding[]` y los acumulan en `session_state`; el LLM solo
   orquesta. **Riesgo residual**: la API de estado compartido de Agno
   (`run_context.session_state`) debe propagarse entre coordinador y miembros;
   `test_tool_accumulates_into_state` y `test_flow_happy_path` lo blindan. Si la
   versión de Agno no lo propaga fiablemente entre members, fallback: cada member
   acumula en su propio `session_state` y `WorkerFlow` mergea ambos tras `arun`.
2. **Structured-output de Opus = único punto LLM en el camino del *reporte*.**
   `synthesize_summary` es el único `output_schema`; smoke-test obligatorio antes
   del demo (§6, §9). Si Agno no detecta bien el structured-output de Claude,
   fallback a `Agent` sin schema + `json.loads` defensivo del texto.
3. **El LLM nunca calcula score/dedup** (07 es dueño): el worker llama funciones
   puras; Opus recibe solo el resumen compacto (<2k tokens). Evita prompts de
   miles de tokens, caros y poco fiables.
4. **Fallo parcial degrada, no rompe** (spec §4): cada tool en `try/except` →
   Finding-meta + `coverage`; `status=partial`, nunca excepción propagada.
   `test_flow_partial_status` es el guard.
5. **Budget/cancel los posee 04**: el worker respeta `CancelToken` + watchdog; no
   reimplementa timeouts (solo el contrato de continuación).
6. **Un único `function` SAQ** (`handle_command`): el pentest reusa el
   command-bus existente; cero cambios a `worker_settings` salvo lo que 08 añada
   en `cron_jobs`.
7. **Modelos centralizados en `ModelFactory`** para poder mockearlos en tests sin
   llamar a la API de Anthropic (todos los tests de §9 salvo el smoke gateado).
8. **Costo Opus**: el coordinador Opus corre por scan; el contraste de costo
   (Opus coordina + redacta vs. Sonnet ejecuta) está acotado porque Opus no ve
   evidence crudo. Si el costo del coordinador preocupa, evaluar Opus solo en
   síntesis y un coordinador Sonnet — decisión abierta, no bloqueante para el
   demo.
