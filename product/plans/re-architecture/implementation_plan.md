---
feature: re-architecture
type: plan
status: implemented
coverage: 90
audited: 2026-06-16
---

# Plan de implementación — Pipelines configurables + Conexiones (entrada/salida)

> **Para Claude Code.** Implementación **de corrido**: un único hilo de fases (F0→F12)
> que entrega el refactor de arquitectura **y** los webhooks/conexiones en secuencia.
> Cada fase es independiente y verificable; no rompe lo existente (strangler-fig).
>
> **Fuentes:** la propuesta está en `plans/architecture/*.html` y los casos en `plans/cases/*.html`; las **decisiones
> cerradas** (A1–A6, B1–B10, W1–W3, D1–D8) en `plans/decisiones.md` — son
> vinculantes. Las specs de referencia: `specs/connections/`, `specs/source_webhooks/`,
> `product/specs/source-webhooks/standard-webhooks.md`, `product/specs/extraction/extra-fields.md`, `product/specs/analysis-rules/_archive/analysis-execution.md`.

---

## 0. Cómo usar este plan

- **Orden:** ejecutar F0→F12 en orden. Cada fase lista sus **dependencias**; no saltear.
- **No romper nada:** cada fase mantiene el comportamiento actual hasta que se la
  referencia. El path STANDARD/ANALYSIS de hoy sigue vivo hasta F2.
- **Gate por fase:** terminar una fase = sus criterios de **verificación** pasan
  (tests + migración aplicada + comportamiento previo intacto). No avanzar si no.
- **Convenciones del repo (obligatorias):**
  - Clean Architecture + DDD: `domain/ → application/ → infrastructure/ → presentation/`.
  - Use cases = dataclasses con `execute()`. Repos abstractos en `domain/`, SQL en `infrastructure/`. Presenters convierten a camelCase. Routers usan `add_api_route()`. Excepciones extienden `DomainError`.
  - Migraciones Alembic en `backend/src/common/database/versions/` (`just migrate-backend-new "nombre"`).
  - Python: snake_case, type hints, async/await. Tests con `expects` (skill `python-testing`); apuntar a cobertura alta (skill `pytest-coverage`).
  - Pipelines/document types/schemas se **versionan inmutables** y se cargan por **fixtures JSON** (`backend/command.py` load/dump, `backend/fixtures/`) — decisión **A1**.
- **Determinismo Temporal:** el cuerpo del workflow (interpretar el pipeline) es
  determinista; el I/O vive en activities. Sellar `pipeline_id`+`version` al arrancar
  el run; recetas inmutables append-only; Worker Versioning / `workflow.patched()`
  para cambios incompatibles del intérprete.

---

## 1. Mapa de anclaje (lo que YA existe — extender, no reescribir)

> Verificado contra el código. **Gran parte de webhooks/conexiones ya está codificada.**

**Webhooks (catálogo, firma, entrega, persistencia):**
- Enum `WebhookEventType` → `backend/src/common/domain/enums/webhooks.py` — hoy solo `document.extracted`, `document.failed`. Status `WorkflowEventDeliveryStatus` (PENDING/DELIVERING/DELIVERED/FAILED/SKIPPED).
- Firma: `backend/src/common/application/helpers/webhooks/signing.py` (`generate_webhook_secret`, `sign_payload`, `SECRET_PREFIX='whsec_'`, `build_signature_headers`).
- Entrega+retry: `.../helpers/webhooks/delivery.py` (`deliver_webhook`, `WebhookDeliveryResult`).
- SSRF: `.../helpers/webhooks/url_validation.py` (`validate_webhook_url`).
- Destino: `backend/src/common/database/models/webhook_destination.py` (`WebhookDestinationORM`); repo iface `backend/src/workflows/domain/repositories/webhook_destination.py`; SQL `.../infrastructure/repositories/sql_webhook_destination.py`; builder `.../infrastructure/builders/webhook_destination.py`.
- Dispatch: `backend/src/workflows/application/document_sets/dispatch_webhooks.py` (`DispatchDocumentSetWebhooks`) + `webhook_dispatcher.py` (`WorkflowWebhookDispatcher`).
- Payload: `.../document_sets/webhook_payload.py` (`build_event_payload`, `PLAIN_TEXT_MAX_BYTES=5MB`, confianza por bbox, camelCase).
- Eventos: dominio `backend/src/common/domain/models/workflow_event.py`; ORM `backend/src/common/database/models/workflow_event.py` (`WorkflowEventORM`, único `doc_type_job_destination`).
- HTTP/admin: `backend/src/workflows/presentation/endpoints/webhook_destination.py`, `.../workflow_webhooks.py`; replay `.../application/workflows/webhook_event_replayer.py`; listado `webhook_event_lister.py`; retry `.../document_sets/retry_pending_events.py`.
- **Summary webhook (¡existe!):** `backend/src/workflows/application/analysis_run_summary/webhook_dispatcher.py` (`SummaryWebhookDispatcher`) — base para `analysis_run.completed`.
- Tenant secret: `backend/src/common/database/models/tenants/tenant.py` (`TenantORM.webhook_signature_key`).

**Connections / Accounts:**
- Enums: `backend/src/common/domain/enums/connections.py` (`ConnectionProvider` WEBHOOK/SLACK/EMAIL/WHATSAPP/DRIVE, `ConnectionCapability` RECEIVE/SEND, `PROVIDER_CAPABILITIES`).
- ORM: `backend/src/common/database/models/connection_account.py` (`ConnectionAccountORM`: provider, capabilities JSONB, status, config JSONB, secret).
- ⚠️ **Duplicación a unificar:** dominio en DOS copias — `backend/src/common/domain/models/processing/connection_account.py` y `backend/src/connections/domain/models/connection_account.py`.
- Repo/CRUD/HTTP completos en `backend/src/connections/{domain,infrastructure,application,presentation}/...`.

**Refactor — pipeline de extracción:**
- `backend/src/workflows/presentation/workflows/pipeline.py` (`run_extraction_pipeline`).
- `.../document_set_processing.py` (`DocumentSetProcessingWorkflow`, `_invoke_lambda`, `_checkpoint`, signals cancel/pause).
- `.../document_set_re_extraction.py` (`DocumentSetFieldReExtractionWorkflow`).
- Nombres lambda: `backend/src/workflows/domain/constants.py` (EXTRACT_TEXT/CLASSIFY_PAGES/EXTRACT_FIELDS/VALIDATE_EXTRACTION).
- Enums: `backend/src/common/domain/enums/workflows.py` (WorkflowType, WorkflowDocumentSetStatus…).

**Refactor — análisis + síntesis:**
- `.../workflows/analysis_run.py` (`WorkflowAnalysisRunWorkflow`); activities `.../activities/analysis_run_activities.py` (`LoadAnalysisRunPlanActivity`, **`knowledge_context=[]` hardcodeado**).
- Reglas: protocolo `backend/src/workflows/domain/rules/kind_protocol.py` (`EvalInputs` con `knowledge_context`, `WorkflowRuleKind`); evaluador `.../application/workflow_rules/evaluation/evaluator.py`; scope `.../scope_resolver.py`; tokens `backend/src/workflows/domain/services/token_resolver.py`.
- Enums eval: `backend/src/common/domain/enums/workflow_rules.py` (`WorkflowRuleScopeMode`, **`WorkflowRuleOnEmpty` SKIPPED/FAILED/PASSED** — ya soporta B10).
- Síntesis: `.../infrastructure/services/run_summary/synthesizer.py` (`SynthesizerAgent.synthesize` valida vs `output_schema`); hash `.../application/analysis_run_summary/hashing.py` (`compute_input_hash`); `complete_run.py`; verdict `backend/src/common/domain/enums/run_summary.py`; summary model `.../models/processing/workflow_analysis_run_summary.py`.

**Modelos/campos:** `document_type.py` (`DocumentType`: fields/validation_rules JSONB), `workflow_document.py` (extraction/mapped_extraction), `workflow_document_set.py` (processing_job_id/last_seq), `workflow_rule*.py`. Auth: `backend/src/common/infrastructure/dependencies/api_keys.py` (`get_admin_api_key`, solo `ADMIN_API_KEY` global).

---

## 2. Secuencia de fases (de corrido)

### F0 · Groundwork compartido
**Objetivo:** base reusable antes de tocar features. **Dep:** ninguna.
- **Secreto revelable + rotación (VO):** extraer el patrón repetido (`webhook_destination.secret`, `tenant.webhook_signature_key`, futuros `api_key`/`hmac_secret` del source) a un value-object/mixin: generar con prefijo, `String(512)`, `reveal()`/`regenerate()`, presenter `hasX`. Unificar el generador `whsec_` de `signing.py`. Prefijos: `whsec_` (HMAC), `dxk_` (API key), `src_` (token ruteable).
- **Unificar `ConnectionAccount` dominio:** colapsar las dos copias (`common/domain/models/processing/` y `connections/domain/models/`) en una sola (preferir `connections/`); actualizar imports.
- **Verificación:** VO con tests; el comportamiento de firma/secreto de webhooks actuales no cambia; imports verdes.

### F1 · Motor de pipelines (M0 · A1)
**Objetivo:** un único intérprete genérico que ejecuta un pipeline-como-dato. **Dep:** F0.
- **Modelos:** `Pipeline` + `PipelineVersion` (DB; `phases` JSONB ordenado, `version` inmutable append-only). Migración Alembic. **Carga por fixtures JSON** vía `backend/command.py` (load/dump) — A1.
- **Contrato de fase:** `PhaseInput`/`PhaseOutput` tipados + un registro `PHASE_LIBRARY` (id → handler).
- **`PhaseExecutor`** + **`PipelineInterpreterWorkflow`** (`@workflow.defn`) que hace `for phase in pipeline.phases: state = await execute_phase(phase, state)`. Sella `pipeline_id`+`version` en el input del run. Reusa `_checkpoint`/eventos `document_set.*` y la disciplina de refs S3 (límite 2 MiB).
- **Equivalencia:** primera receta = réplica exacta de `run_extraction_pipeline`.
- **Verificación:** golden-run — un run por el intérprete produce los **mismos** `WorkflowDocument`/eventos que `DocumentSetProcessingWorkflow` para el mismo input. Worker Versioning configurado.

### F2 · Envolver fases existentes (M1)
**Objetivo:** las lambdas actuales pasan a ser fases de la librería. **Dep:** F1.
- Envolver cada `_invoke_lambda` (constants `EXTRACT_TEXT`/`CLASSIFY_PAGES`/`EXTRACT_FIELDS`/`VALIDATE_EXTRACTION`) como fase tipada; agregar `ingest` y `finalize`.
- Expresar la **re-extracción** (`DocumentSetFieldReExtractionWorkflow`) como una **receta subset** (`extract_fields`+`validate`) en vez de un workflow aparte → marcar el workflow viejo como deprecado.
- **Verificación:** el pipeline STANDARD y la re-extracción corren por el intérprete con paridad; `DocumentSetFieldReExtractionWorkflow` sin tráfico nuevo.

### F3 · Webhooks de salida configurables (D4 · W1 · D8 · §11.8)
**Objetivo:** cualquier pipeline emite webhooks; payload por output. **Dep:** F2 (finalize). *Mayormente generalizar lo existente.*
- **Generalizar `webhook_destinations` → `workflow_destinations` in-place (D4):** ALTER `+provider` (default `WEBHOOK`), `+account_id` nullable; **rename de tabla**; redirigir `dispatch_webhooks.py`, `webhook_dispatcher.py`, `workflow_events.destination_id`, repos/builders/endpoints. WEBHOOK idéntico al actual.
- **Catálogo (W1):** agregar `analysis_run.completed` a `WebhookEventType`. El payload de resultado = el `output_schema` del pipeline (no un evento por caso). `subscribed_events` default **derivado del output** del pipeline (D8).
- **Desacoplar el dispatcher:** cablear `SummaryWebhookDispatcher` en la completitud del `WorkflowAnalysisRunWorkflow`/fase `finalize` para que ANALYSIS emita `analysis_run.completed`. (Hoy solo `pipeline.py` dispara, gateado por `persist`.)
- **Verificación:** un pipeline de extracción emite `document.extracted`; uno de análisis emite `analysis_run.completed` con su `output_schema`; entregas se loggean en `workflow_events` (idempotencia intacta).

### F4 · Confianza por campo + gate (M2 · A6)
**Objetivo:** confianza por campo persistida que dispara el gate/HITL. **Dep:** F2.
- **Persistir** confianza por campo en `WorkflowDocument` (`{campo: {value, confidence, source}}`); hoy `webhook_payload.py:_leaf_confidence` la calcula al vuelo (min de bbox). `confidence_threshold` de `product/specs/extraction/extra-fields.md` queda **cableado**.
- **A6 por capas:** legibilidad (bbox) + semántica (auto-eval LLM y/o consenso `analysis_consensus_samples`) + cross-check contra referencia.
- **Fase `confidence_gate`:** umbral por campo (declarativo); **solo etiqueta** `needsClarification`, **nunca falla el run**; default passthrough.
- La re-extracción **recalcula y re-persiste** la confianza (y el payload del webhook refleja los nuevos scores).
- **Verificación:** documento con confianza baja → campos `needsClarification` correctos; gate no tumba el run.

### F5 · Tools: registro + enrich + KB (M3 · A2 · A3 · B1 · B2)
**Objetivo:** llamar servicios externos como Tool tipada desde una fase/regla. **Dep:** F2, F4 (para el enrich condicional por confianza).
- **`ConnectionCapability += LOOKUP` (A3).** `ToolDefinition` (org-level: `name`, `input_schema`, `output_schema`, `transport`, `connection_account_id`). El secreto vive en `ConnectionAccount` (reusar; 3 capabilities RECEIVE/SEND/LOOKUP).
- **Conector determinista** (fuera del LLM): timeout, reintentos con jitter, idempotencia, **circuit breaker**, allowlist SSRF de hosts por `ConnectionAccount` (distinto del SSRF de destinations). **B1: sin caché** para la póliza — fetch en vivo + **snapshot por-caso** de la respuesta (auditoría, no caché reusable) + path `degraded` si el servicio cae.
- **Fase `enrich`** (pre-fetch, A2 default) que escribe el resultado en los datos del caso; + **token `@tool.x(args)`** (A2, lookup puntual desde regla) — ambos por el mismo conector. Soporta `when:` condicional (circulares: enrich solo si `juez_nombre.confidence < umbral`).
- **Inyección de KB (fix):** poblar `EvalInputs.knowledge_context` (hoy `analysis_run_activities.py` lo pasa `[]`) → habilita **B2** (normalización de fármaco vía KB provista por el cliente, `#kb`).
- **Verificación:** una regla/fase resuelve un campo vía Tool; el LLM nunca ve un 401/429; `knowledge_context` llega poblado.

### F6 · HumanTask + fases de pausa (HumanTask · B4 · B10)
**Objetivo:** pausas durables para humano/datos. **Dep:** F2 (signals).
- **Entidad `HumanTask` unificada** (reemplaza `ClarificationRequest`+`ReviewTask`): `kind` (clarification|approval), `status`, `assignee_mode` (internal_queue|external_callback), **`audience`** (doxiq_analyst|bank_analyst…), `payload`, `resolution`, `pipeline_run_id`, `expires_at`.
- **Fases de pausa** (todas: `wait_condition` + reanudar por `signal task_resolved`):
  - `await_clarification` (HITL farmacia, external_callback → emite `needs_clarification`).
  - `human_review` (aprobación; internal_queue **o** external_callback → emite `review.pending`; circulares encadena **dos** con `audience` distinta, B4).
  - `await_documents` (system-wait por completitud; **capacidad** — garantías NO la usa).
- **B10 (garantías incremental):** reusar **`WorkflowRuleOnEmpty.SKIPPED`** (ya existe) — el análisis corre con ≥1 documento; reglas sin sus docs → SKIP; re-evalúa al llegar más. **Sin** `await_documents` como barrera.
- Catálogo: agregar `review.pending` y `needs_clarification` a `WebhookEventType` (HITL).
- **Verificación:** un run se pausa en `human_review`, sobrevive un restart del worker, y reanuda con `POST /review`/`/resolve`; garantías procesa con 1 solo documento.

### F7 · Síntesis con documentos + output_schema (M6 · W1 · A4)
**Objetivo:** la salida final refleja documentos y se cachea bien. **Dep:** F2.
- **Pasar `mapped_extraction`** al `SynthesizerInput` (hoy `synthesizer.py` solo recibe verdicts + rule outputs); **flag por pipeline** (A4) `synthesis_uses_documents`.
- **`input_hash` (A4):** regla de oro — todo lo que entra al prompt entra al hash (`hashing.py:compute_input_hash` hoy excluye `mapped_extraction` por diseño). Versionar la clave de caché.
- **W1:** `analysis_run.completed.payload = output_schema` del pipeline (cobertura/resolución/circular lo dice el schema). `SynthesizerAgent.synthesize` ya valida vs `output_schema`.
- **Verificación:** circulares produce salida con la lista de personas; dos extracciones distintas con mismos verdicts pero distinto contenido **no** reusan síntesis stale.

### F8 · Entrada configurable: Sources + ingest webhook (W2 · D1 · D3 · D5 · D6 · D7 · webhooks F2)
**Objetivo:** toda ingesta de archivos = Source configurable. **Dep:** F1/F2 (disparo del pipeline).
- **`workflow_sources`** (D1) en módulo **`connections`** (D5): `workflow_id`, `provider` (WEBHOOK activo; DRIVE/EMAIL/WHATSAPP modelados), `account_id` nullable (NULL para WEBHOOK), `config` jsonb, `enabled`, **`route_token` columna dedicada única** (D7). Generaliza la `source_webhooks` de spec.
- **Endpoint `POST /v1/ingest/{token}`:** resuelve `route_token → workflow_source → workflow → pipeline`; descarga el/los archivo(s) a S3; dispara el `PipelineInterpreterWorkflow`. **Auth (D3/D6):** `auth_mode` por source, default `api_key` (`X-Api-Key: dxk_…` vs hash) o HMAC (firma body + timestamp anti-replay). Reusa `url_validation` / firma / S3 / Temporal.
- **W2:** los uploads de archivos de los casos (farmacia A, circulares, garantías) pasan a ser sources (el upload HTTP es el source webhook). El **batch diario** (circulares B9/W3) se difiere como un source más (Drive/SFTP) — el modelo ya lo admite.
- **Verificación:** un POST a `/v1/ingest/{token}` con auth válido sube a S3 y arranca el pipeline correcto; token inválido → 401/404; identidad ruteable única garantizada por la DB.

### F9 · API M2M + endpoints de control (M4 · W2)
**Objetivo:** auth M2M y la entrada de datos estructurados (no-archivo). **Dep:** F1.
- **`TenantApiKey`** (M2M tenant-scoped): emisión, hash, resolución a `tenant_id`, dependencia FastAPI que conviva con el JWT de usuario. Hoy solo `ADMIN_API_KEY` global (`api_keys.py`).
- **Endpoints de datos estructurados (W2, NO son sources):** `POST /v1/case` (re-entrada de datos validados, farmacia B), `POST /v1/cases/{id}/review` y `/tasks/{id}/resolve` (callbacks de HumanTask). `GET /v1/jobs/{id}` (thin wrapper sobre `WorkflowDocumentSet`/`AnalysisRun` status; reusa el getter existente y los SSE).
- **`pharmacy_id`/`policy_id` = passthrough** (no entidad) → se reenvían a la Tool.
- **Verificación:** un cliente con API key M2M crea caso, sube por source, recibe resultado por webhook; los callbacks reanudan los HumanTask.

### F10 · UI (review surface, tools, pipelines, conexiones)
**Objetivo:** las pantallas nuevas/cambiadas. **Dep:** F5, F6, F8.
- **Cola/UI de revisión** (preview + resultados editables) — reusa el split-pane de "document detail". Circulares: dos audiencias hospedadas por Doxiq (B4). Garantías: callback (el banco renderiza con los datos).
- **Tools registry**, **constructor de pipelines** (sobre la def en DB/fixtures), **API Keys** (settings), **Conexiones** (sources/destinations + selección de `ConnectionAccount`, sin re-pedir credenciales — webhooks F4).
- **Verificación:** un analista aprueba en la cola → `task_resolved` → el run continúa.

### F11 · Plataforma de eval (A5) — workstream paralelo
**Objetivo:** medir regresiones de extracción. **Dep:** F2 (puede correr en paralelo desde aquí).
- Datasets gestionados (golden sets por document type/pipeline), métricas, comparación de versiones, UI de revisión de evals. Apoyado en el versionado inmutable de pipelines/doctypes (gratis por A1).
- **Verificación:** un cambio de prompt/schema corre contra los golden sets y reporta el delta.

### F12 · Providers TODO (webhooks F5)
**Objetivo:** completar adapters más allá de HTTP. **Dep:** F3 (dest), F8 (source).
- **Sources:** Drive (carpeta), Email (alias), WhatsApp (kapso) — OAuth/kapso + `account_id`. **Dests:** Drive (JSON), Slack (notifica). Evento `document.received` (lo pide Slack §2a).
- Uno por provider; el enum + `config` jsonb + `account_id` ya los soportan.

---

## 3. Orden de dependencias (resumen)

```
F0 ─┬─ F1 ─ F2 ─┬─ F3  (webhooks salida)
    │           ├─ F4 ─ F5  (confianza → tools)
    │           ├─ F6  (HumanTask/pausas)
    │           ├─ F7  (síntesis/output_schema)
    │           ├─ F8  (sources/ingest)
    │           └─ F9  (API M2M / control)
    │
    F10 (UI)  ← F5, F6, F8
    F11 (eval) ← F2 (paralelo)
    F12 (providers) ← F3, F8
```

**Camino crítico:** F0 → F1 → F2 → (F3 ∥ F4→F5 ∥ F6 ∥ F7 ∥ F8 ∥ F9) → F10 → F12.
F3 (webhooks salida) es de bajo riesgo (generalizar) y puede ir apenas exista `finalize`.

---

## 4. Riesgos y mitigaciones

- **Determinismo Temporal** al introducir el intérprete → cuerpo puro + Worker Versioning; golden-runs de equivalencia (F1).
- **Migración `webhook_destinations`** in-place (F3) → ALTER reversible + tests del path WEBHOOK actual antes/después.
- **Escala de listas** (circulares, cientos de personas) → validación por lotes + límite blando configurable (B6).
- **Dependencia de servicios del cliente sin caché** (B1) → path `degraded` + snapshot por-caso auditable.
- **`input_hash`** ampliado (F7) → invalida la caché de síntesis existente → versionar claves, monitorear hit-rate.

## 5. Fuera de alcance (por ahora)
- Adapters no-HTTP de conexiones (F12 los aborda incrementalmente).
- DAG con paralelismo real entre fases (decisión §11.1: lineal + `when:` alcanza para los 3 casos; diferido).
- Contrato A/B/C de farmacia a confirmar con el cliente antes de congelar (B3).

---

> **Cierre:** al terminar F0–F9 el motor de pipelines configurables y los
> webhooks/conexiones quedan operativos de punta a punta (entrada configurable →
> pipeline → salida configurable). F10–F12 completan UI, eval y providers.
> Registro de decisiones: `plans/decisiones.md`.
