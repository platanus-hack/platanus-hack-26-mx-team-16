---
feature: re-architecture
type: plan
status: implemented
coverage: 93
audited: 2026-06-16
---

# Re-arquitectura Doxiq — de workflows monolíticos a pipelines de fases componibles

**Fecha:** 2026-06-09 · **Branch:** `feat/re-arch` · **Estado:** **E1–E6 implementados (2026-06-10)** — **los 4 casos completos** (1 farmacias, 2 fondos de garantía, 3 circulares judiciales con fan-out, 4 pedidos multicanal email+WhatsApp+ASR). E6: editor visual de pipelines (diff pre-publish), UI de policies + QA sampling, export/import bundle + plantillas, canales nativos provider-agnóstico (mailpit/mailgun/WhatsApp Cloud) con dedup delivery-first, extractor `asr` (Gemini) desplegado a AWS dev. Suite 1590+ verde; E2E vivos de los 4 casos con Playwright + canales reales. Diseños E4–E6 consolidados en los ADR 0001–0006. Pendiente: commitear; revisar drift menor de reglas pre-E2 ya cerrado en E5.
**Documento hermano:** `product/plans/re-architecture/mockups/cases.html` (mapeo visual de los 5 casos con diagramas).

---

## 1. Resumen ejecutivo

El Caso 1 (agrupador de seguros / farmacias por WhatsApp) **no se resuelve bien con la arquitectura
actual**, pero no porque falte la idea — falta terminarla. En `feat/re-arch` ya conviven **dos motores**:
el legacy de secuencia fija (`DocumentSetProcessingWorkflow`) y un intérprete genérico
"pipeline-as-data" (`PipelineInterpreterWorkflow`) que ya ejecuta fases configurables, pausas humanas
durables y enriquecimiento con tools. El problema es que el motor nuevo solo es alcanzable desde la
ingesta por webhook, el análisis de reglas vive desconectado (se dispara a mano), no existe entrada de
datos sin documento, y el resultado de la extracción no es recuperable por API key.

**La propuesta no es una arquitectura nueva: es elegir el intérprete como ÚNICO motor y elevarlo.**

1. **Un solo motor**: todo procesamiento (upload de UI, ingesta webhook, API M2M) corre por
   `PipelineInterpreterWorkflow`; el flujo actual se convierte en la receta `standard@v1`.
2. **El expediente (`WorkflowCase`) como agregado central**, con política de completitud, cierre
   explícito y estado público (máquina de estados estilo Rossum).
3. **Todo dato es un documento** — los datos validados que inyecta un cliente y los resultados de
   tools externas se persisten como *documentos virtuales* con doc-type y slug, de modo que el motor
   de reglas (`@slug.path`) funciona sin cambios.
4. **Confianza como contrato de dos capas + señales cualitativas**, y la **clarificación estructurada**
   (webhook `needs_clarification` + endpoint de corrección) como primitivo del producto.
5. **Revisión humana por etapas tipadas** (analista interno → analista del cliente) gobernada por una
   `ActivationPolicy` declarativa.
6. **Tools hacia servicios web del cliente** (lookup de póliza, BD de jueces) como fase `enrich`
   firmada y con retries — **ningún IDP mainstream lo ofrece nativo: es el diferenciador**.

Con eso, los cinco casos (farmacias, fondos de garantía, circulares judiciales, pedidos
multicanal, CV-vs-puesto) se expresan como **recetas distintas del mismo catálogo de fases**,
sin código por cliente salvo la configuración.

---

## 2. Estado actual (lo que hay en `feat/re-arch`)

### 2.1 Dos motores y medio

| Pieza | Estado | Dónde |
|---|---|---|
| `DocumentSetProcessingWorkflow` | Motor **legacy**: OCR → classify_pages → extract_fields → validate_extraction, 4 Lambdas hardcodeadas (`vnext-tools-*-{STAGE}`), disparado por TODOS los uploads normales | `backend/src/workflows/presentation/workflows/document_set_processing.py`, `pipeline.py` |
| `PipelineInterpreterWorkflow` | Motor **nuevo** "pipeline-as-data": carga `PipelineVersion` inmutable y ejecuta `phases` JSONB; **solo alcanzable desde `/v1/ingest/{token}`** | `presentation/workflows/pipeline_interpreter.py`, `application/pipelines/runtime.py` |
| `DocumentSetFieldReExtractionWorkflow` | Tercer camino: re-extracción que duplica plumbing | `presentation/workflows/document_set_re_extraction.py` |
| `WorkflowAnalysisRunWorkflow` | Evaluación de reglas con fan-out (semáforo 4), **solo disparo manual por endpoint**, no es fase | `presentation/workflows/analysis_run.py` |

Fases ya registradas en el intérprete (`application/pipelines/`): `ingest`, `extract_text`,
`classify_pages`, `extract_fields`, `validate_extraction`, `finalize`, `confidence_gate`,
`enrich` (activity `tool_lookup` con connector determinista), `human_review`, `await_clarification`,
`await_documents` (pausas durables vía `HumanTask` + señal `task_resolved`).

### 2.2 Modelos que ya rompieron el molde

- **`WorkflowCase`** (`workflow_cases`): el expediente existe, con status propio
  (`DRAFT/IN_PROGRESS/COMPLETED/ARCHIVED`) y es la unidad del análisis (`workflow_analysis_runs.workflow_case_id NOT NULL`).
- **`HumanTask`** (`human_tasks`): pausa durable unificada — `kind` (`clarification`/`approval`),
  `assignee_mode` (`internal_queue`/`external_callback`), payload/resolution, expiración.
- **`Pipeline` / `PipelineVersion`** (`pipelines` / `pipeline_versions`): recetas versionadas
  inmutables (`phases` JSONB, `output_schema`).
- **`field_confidence`** en `WorkflowDocument`: `{campo: {value, confidence, source}}` — hoy solo capa
  bbox/OCR (mín. de confidences de Textract), umbral 0.6, `needs_clarification` etiqueta sin frenar.
- **Reglas**: compilación versionada (`WorkflowRuleCompilation`), kinds `VALIDATION`/`DERIVATION`,
  **scopes cross-documento ya soportados** (`TUPLE_CARTESIAN`, `AGGREGATE_OVER_TYPE`, `SINGLE_DOCUMENT`,
  `ALL_DOCUMENTS` + `on_empty`), handlers deterministas (format, range, date, checksums luhn/IBAN/RUT,
  cross_ref, aggregate) y fallback `llm_check`.
- **Salida**: `WorkflowAnalysisRunSummary` con verdict determinista (`PASS/FAIL/REVIEW`), señales por
  severidad/polaridad, `confidence_score`, y `output` JSONB validado contra `output_schema`
  (spec `product/plans/case-output/case-output.md`: proyección `x-source` + LLM solo para el resto, provenance `Citation`).
- **Entrega**: `WorkflowEvent` outbox + `workflow_destinations` multi-destino (tabla renombrada
  desde `webhook_destinations` en esta branch), firma HMAC estilo Svix
  (`Doxiq-Id/Timestamp/Signature`, `product/specs/source-webhooks/standard-webhooks.md`).
- **M2M**: API keys `dxk_`, ingesta pública `POST /v1/ingest/{token}` (202 + job_id),
  `GET /v1/jobs/{job_id}` (solo estado), `POST /v1/tasks/{task_id}/resolve` (funcional),
  `POST /v1/case` (**stub**: 202 + echo, "pipeline not yet wired").

### 2.3 Los 10 supuestos rígidos que estorban

1. **Doble motor**: el upload normal nunca pasa por el intérprete (`application/document_sets/dispatcher.py`).
2. Lambdas y orden **hardcodeados** (`domain/constants.py:24-27`), extractor fijo `TEXTRACT_LAYOUT`.
3. **1 archivo = 1 document_set = 1 run**; split solo dentro de `classify_pages` (páginas contiguas), sin fan-out.
4. `extract_fields`/`validate_extraction` = **una invocación para todo el set** (sin granularidad por doc).
5. **El análisis no es fase ni se encadena** — solo endpoint manual.
6. `PipelineState` con slots nominales de la familia extracción (`runtime.py:42-60`); fases nuevas van a `scratch`.
7. Predicados `when` limitados a `<campo>.confidence` y claves de scratch; predicado roto ⇒ la fase corre igual.
8. Constantes embebidas: concurrencia 4, retries 2, umbral 0.6, cola Temporal única.
9. **Confianza solo bbox**, calculada una vez; sin capa LLM ni señales cualitativas.
10. Sin extracción recuperable por API key, sin entrada data-only, sin versionado de doc-types/schemas
    (JSONB mutable en `workflows`), sin corrección de campos en UI (data-pane read-only).

---

## 3. Hallazgos de mercado

Plataformas analizadas: Extend, Reducto, Rossum, Hyperscience, Instabase AI Hub, ABBYY Vantage,
Azure Document Intelligence / Content Understanding, AWS GenAI IDP Accelerator, Unstructured.io,
Sensible, Docsumo, Nanonets, Klippa DocHorizon, AWS A2I, Ocrolus, Heron Data, y la capa conversacional
(Casca, Sprout.ai, Tungsten, Alan).

### 3.1 Qué hace cada una (lo relevante)

| Plataforma | Modelo de pipeline | Lo que vale la pena copiar |
|---|---|---|
| **Extend** | Processors (Parse/Split/Classify/Extract) versionados draft→publish→pin + Workflows con conditional steps por confidence; run con máquina de estados `NEEDS_REVIEW` de primera clase | Estado `NEEDS_REVIEW` con webhook propio; endpoint **Correct Workflow Run Outputs** (corrección sin re-procesar); pin de versiones por run |
| **Reducto** | APIs stateless (/parse, /extract, /extract_async) + Pipelines del Studio con `pipeline_id` estable que apunta a la config desplegada (Config History) | `jobid://` reusable (re-extraer sin re-OCR); `parse_confidence` vs `extract_confidence` separadas; webhooks vía Svix |
| **Rossum** | Queues con schema + umbrales + hooks; documento = máquina de estados pública (`importing→to_review→reviewing→confirmed→exported`, estado `split`) | Lineage padre-hijo en split (padre queda `split`); verificación **por campo** (tick auto vs humano); panel de "automation blockers"; Tab solo entre campos pendientes; umbral default 0.975 |
| **Hyperscience** | Flows de Blocks (SDK declarativo) + Releases obligatorios para estar Live | **Tareas de supervisión tipadas por fase** (clasificación ≠ transcripción ≠ excepción); QA sampling (% de casos confiables auditados, mide a la máquina Y al analista); Code Blocks como escape hatch |
| **Instabase** | App version = snapshot inmutable de TODO (campos+validaciones+settings); Deployments fijan versión | Review queue + **Escalation queue** con grupos; review-by-file vs review-by-run; las validaciones SON el gate de revisión |
| **ABBYY Vantage** | Catálogo de Skills reutilizables + Process Skill que clasifica primero y enruta después | Catálogo/marketplace de configs de extracción; splitting como activity con modos |
| **Azure DI / CU** | Analyzer declarativo JSON (classify+split+extract en una llamada); `splitMode {none\|perPage\|auto}` | Convención LRO `202 + Operation-Location`; splitMode como parámetro simple |
| **AWS IDP Accelerator** | Step Functions con fases explícitas, incl. **Assessment** (LLM puntúa confianza contra la evidencia, con explicación textual) | "Assessment" como fase separada de la extracción; config-driven sin redeploy; umbral típico 70–85% |
| **Unstructured** | Único DAG real (ETL para RAG, sin HITL) | Validación de orden entre tipos de nodo; estrategias fast/hi-res/VLM con tradeoff explícito |
| **Sensible** | Config-as-code (SenseML en git del cliente); Portfolio para mailroom (fingerprint vs LLM) | **Señales cualitativas** (`multiple_possible_answers`, `answer_may_be_incomplete`) — se traducen directo en una pregunta de WhatsApp; export/import de configs versionable |
| **Docsumo / Nanonets / Klippa** | Review stages secuenciales (regla fallida ⇒ flag ⇒ no avanza); revisores por stage (por-excepción vs mandatory); HITL como nodo del flow | Stage 1 = interno mandatory, Stage 2 = cliente mandatory; pool con auto-asignación; **lock pesimista** por documento; comentarios + audit log por campo; colores verde/amarillo/rojo |
| **AWS A2I** | Flow Definition = work team + task template + **activation conditions declarativas** (JSON: umbral por key, rangos, sampling) | `ActivationPolicy` versionable y editable sin deploy; separar quién/qué/cómo |
| **Ocrolus** | Book = caso multi-doc; HITL **como servicio del proveedor** dentro del SLA (85%→99% accuracy); completeness report del paquete | El tier-1 de Doxiq es exactamente esto; ground-truth set por workflow; consenso multi-LLM como pre-filtro barato |
| **Heron Data** | Caso = end_user; **cierre explícito** `PUT ready-for-processing` dispara el análisis | Trigger limpio de "expediente completo" |
| **Google Document AI** | HITL nativo **deprecado** (ene-2025) | Valida la tesis: la revisión vive en la capa que conoce el negocio, no en el OCR |
| **Casca / Alan / Twilio+IDP** | Nadie IDP conversa; en LatAm domina bot del cliente + IDP stateless con confidence | **Doxiq no debe ser dueño del canal WhatsApp**: emitir clarification requests estructuradas; el tool-calling a servicios del cliente NO existe como producto — hueco de mercado |

### 3.2 Patrones transversales (el consenso de la industria)

1. **Vocabulario canónico convergente**: ingest → parse/OCR → split → classify → extract →
   assess/validate → review → enrich → output → deliver. Adoptarlo sin miedo.
2. **Dos capas**: componente versionado reutilizable (processor/skill/block/config) + workflow que
   ordena y enruta. El run registra las versiones exactas que usó.
3. **Versionado = ID estable + puntero + historial + snapshot en runs** (Reducto/Extend/Instabase/Hyperscience).
4. **Lineal con ramas condicionales, no DAG arbitrario** — solo Unstructured es DAG real y es ETL.
   Para el dominio de Doxiq, lista ordenada + `when` es suficiente y mucho más explicable.
5. **Mailroom = split+classify fusionados con lineage padre-hijo** y rangos de páginas; la clase del
   hijo selecciona su config de extracción downstream.
6. **La confianza es la moneda de routing**: por campo, dos capas (parse vs extract), con señales
   cualitativas y citations; umbrales configurables deciden auto vs revisión.
7. **HITL tipado por fase, no cola genérica**; multinivel = stages secuenciales con pools propios;
   lock por caso; el siguiente nivel solo toca lo no verificado.
8. **API: dos planos** — extracción stateless (sync/async) + agregado "caso" con completitud
   consultable y cierre explícito. Convención 202 + status URL + webhooks firmados con event-id
   (idempotencia) y replay.
9. **Corrección sin re-procesar**: endpoint para inyectar valores validados que re-evalúa solo lo
   downstream (reglas), nunca re-OCR.
10. **NEEDS_REVIEW / NEEDS_CLARIFICATION como estados de primera clase** con webhook dedicado.
11. **Escape hatches en los bordes de fase** (code blocks, hooks, lambdas) — en Doxiq: la fase `enrich`.
12. **Config exportable/versionable** (git-able) habilita dev/prod, peer review y catálogo de plantillas.

---

## 4. Propuesta de arquitectura

### 4.1 Principios

1. **Un solo motor.** `PipelineInterpreterWorkflow` ejecuta todo; el legacy se congela como receta
   `standard@v1` y se elimina el workflow monolítico cuando la paridad esté probada.
2. **El expediente (`Case`) es el agregado central.** Documentos, datos inyectados, resultados de
   tools, runs de análisis, tareas de revisión y output cuelgan del caso. Máquina de estados pública:
   `RECEIVING → PROCESSING → NEEDS_CLARIFICATION | NEEDS_REVIEW → ANALYZING → REVIEW_L1 → REVIEW_L2 → COMPLETED | REJECTED | FAILED`.
   El estado es del **caso**; cada documento se procesa individualmente al llegar (un caso puede
   seguir en `RECEIVING` por completitud con documentos ya extraídos — estado por documento ≠ estado del caso).
   `NEEDS_CLARIFICATION`/`NEEDS_REVIEW` son desvíos reentrantes: pueden colgar de `PROCESSING`
   (gate de confianza) o de `ANALYZING` (reglas bloqueantes). `FAILED` es alcanzable desde cualquier estado.
3. **Todo dato es un documento.** Entrada data-only (Caso 1B) y resultados de tools (`enrich`) se
   materializan como **documentos virtuales** (`WorkflowDocument` con `source=EXTERNAL_DATA|TOOL`,
   `extraction=payload`, doc-type propio). Así `@poliza.coberturas` o `@datos_validados.medicamentos`
   funcionan en reglas y output **sin tocar el motor de reglas**.
4. **Pipeline = lista ordenada de fases con `when`**, versionada e inmutable (ya existe). Nada de DAG
   visual: stepper vertical, condicionales y fan-out de split bastan (consenso de mercado).
5. **Confianza = contrato**: `parse_confidence` (OCR/bbox — ya existe) + `extract_confidence`
   (LLM/assessment — nueva) + señales cualitativas + citations. Por campo, siempre en la API.
6. **Revisión por etapas tipadas** con `ActivationPolicy` declarativa (umbral por campo, reglas
   bloqueantes, sample_rate) — las reglas SON el gate (patrón Instabase).
7. **Webhooks por checkpoint** del ciclo de vida del caso, sobre la infraestructura ya construida
   (outbox + HMAC Svix-style).

### 4.2 Catálogo de fases (la unidad de composición)

| Fase | Estado | Notas |
|---|---|---|
| `ingest` | ✅ existe → ⬆️ | + canales: API y source webhook (ya); `caseId` find-or-create (E4); sources nativos de **email** (buzón por workflow) y **WhatsApp Business** para media (E6 — `ConnectionProvider.EMAIL/WHATSAPP` ya en enums; hasta entonces el sistema del cliente reenvía por API) |
| `extract_text` | ✅ existe → ⬆️ | config: `extractor` (`textract_layout` \| `documentai` \| `vlm` para manuscritos \| `asr` para audio de voz/llamadas — E6) — hoy fijo |
| `split_classify` | ✅ existe (`classify_pages`) → ⬆️ | + `split_mode: none\|per_page\|auto`, `expected_types[]` (acota mailroom), `fan_out: inline\|child_cases` (**nuevo**: child workflows Temporal, lineage `parent_case_id`) |
| `extract_fields` | ✅ existe → ⬆️ | + invocación **por documento** (hoy: todo el set en una llamada) para granularidad de retry/fan-out |
| `assess` | 🆕 | Capa-2 de confianza: LLM puntúa cada campo contra la evidencia, emite `extract_confidence` + señales (`multiple_possible_answers`, `answer_may_be_incomplete`, `illegible`) con explicación (patrón AWS Assessment + Sensible) |
| `validate_extraction` | ✅ existe | validaciones de formato por campo (cédula, NIT, montos) — ya hay handlers checksum |
| `confidence_gate` | ✅ existe → ⬆️ | se convierte en evaluador de **`ActivationPolicy`**: decide `continue` / `clarify` / `review` |
| `enrich` | ✅ existe → ⬆️ | `tool_lookup` se extiende a **HTTP tools firmadas** contra servicios del cliente (póliza, BD de jueces); resultado ⇒ documento virtual `@slug`; `when` condicional por confianza |
| `await_documents` | ✅ existe → ⬆️ | + **CompletenessPolicy** del pipeline (`required_types: {anexo:1, evaluacion:1, resolucion:1}` — un 4º tipo de documento es solo una entrada más), endpoint de completeness, cierre explícito `POST /v1/cases/{id}/ready` o `auto_ready` opcional (flag en la policy, default false) |
| `await_clarification` | ✅ existe → ⬆️ | emite **clarification request estructurada** por webhook (campo, motivo, candidatos, doc faltante); respuesta por `POST /v1/tasks/{id}/resolve` (ya funcional) |
| `human_review` | ✅ existe → ⬆️ | + `stage` (`internal` \| `client`), pool por stage, lock, verificación por campo, mandatory vs by-exception |
| `analyze` | 🆕 (envuelve lo existente) | dispara `WorkflowAnalysisRunWorkflow` como **child workflow** y espera su resultado (decisión D3 §8.1 — conserva fan-out/SSE/cancel y estrena los child workflows que el split del Caso 3 reutiliza); hoy solo manual |
| `output` | 🆕 (envuelve lo existente) | proyección `x-source` + síntesis LLM contra `output_schema` (spec case-output) como fase explícita |
| `deliver` | 🆕 (envuelve lo existente) | emite eventos al outbox → webhook destinations / conexiones; hoy enterrado en `finalize`/`complete_run` |

**Sustrato de ejecución (las Lambdas).** Las fases de cómputo se resuelven en activities Temporal
que invocan las **Lambdas de procesamiento** (`vnext-tools-extract_text/classify_pages/extract_fields/
validate_extraction`) — hoy con nombre, orden y extractor hardcodeados (`domain/constants.py:24-27`).
La propuesta las registra en un catálogo `phase_kind → lambda (alias/versión)` configurable por fase
dentro de la `PipelineVersion`, con **pin de versión de Lambda por run** (mismo trato que la receta):
cambiar de extractor OCR, probar una Lambda nueva o tener variantes por tenant es configuración, no
deploy del worker. Fases nuevas (`assess`, `enrich` HTTP) pueden ser Lambdas o activities locales —
el contrato de la fase no cambia.

**Scope de fase (el modelo de ejecución).** Cada fase declara `scope`: las fases **document**
(`ingest → extract_text → split_classify → extract_fields → assess → validate_extraction`) corren
**por cada documento al llegar**; las fases **case** (`await_documents`, `confidence_gate`, `enrich`,
`await_clarification`, `analyze`, `human_review`, `output`, `deliver`) corren **una sola vez** en el
workflow del expediente, que se pausa en la primera fase case no satisfecha. Así la receta sigue
siendo una lista lineal legible y "cada documento se procesa al llegar" tiene semántica precisa:
no hay loop hacia atrás — llegan documentos, corren sus fases document, y el caso avanza cuando el
gate case-scope se satisface.

Runtime: generalizar `PipelineState` a un **mapa de artefactos por fase** (S3 refs + metadatos, nunca
payloads >2 MiB inline por el límite de Temporal) y endurecer `when` (predicado inválido ⇒ error de
configuración al publicar la versión, no silencio).

### 4.3 Modelo de datos — cambios concretos

| Tabla | Cambio |
|---|---|
| `workflow_cases` | + `status` ampliado (máquina de estados §4.1), `parent_case_id` (lineage de split), `pipeline_version_id` (snapshot), `ready_at`, `external_ref` (id del sistema del cliente), `completeness` JSONB calculado |
| `workflow_documents` | + `source` ampliado: `SINGLE/BULK/SPLIT_CHILD/EXTERNAL_DATA/TOOL`; + `parent_document_id` (oficio→TIFF); + `extract_confidence` y `signals` JSONB (capa 2); + `verification` JSONB por campo `{value, verified_by, level, verified_at, previous_value}` |
| `pipelines` / `pipeline_versions` | ya correctos; + `activation_policy` JSONB y `completeness_policy` JSONB en la versión |
| `human_tasks` | + `stage` (`internal`/`client`), `queue_id`/pool, `assignee_id`, `locked_by/locked_at`, `case_id` ya existe |
| `workflow_rules` | + `slug` único por workflow (requisito del spec case-output para `@rule.<slug>`); + `severity` ya existe en señales — exponer `blocking` |
| `document_types` | desacoplar a catálogo org-level con **versionado de schema** (hoy `fields` JSONB mutable); `workflow_document_types` ya existe como join |
| 🆕 `tool_definitions` | `connection_account_id`, `slug`, método/URL template, auth, `input_schema`/`output_schema`, firma + retries; resultado se persiste como documento virtual |
| 🆕 `case_events` | timeline append-only del caso (fase iniciada/completada, gates, correcciones) — alimenta UI y webhooks |

### 4.4 API pública — dos planos

**Plano 1 — extracción stateless** (Caso 1A; lo que esperan los integradores):

```
POST /v1/extract                  (X-Api-Key dxk_)
  multipart file | {url} | {base64}
  ?mode=sync (≤5 páginas, D1; timeout o exceso de páginas ⇒ degrada a 202 — nunca error)
  ?pipeline=<slug>  (opcional; default: receta "extract-only")
  → { documents: [{type, fields: {v, parse_confidence, extract_confidence,
       signals[], citations[]}}], job_id }
GET  /v1/jobs/{id}                → estado + RESULTADO (hoy: solo estado — gap crítico)

Run "efímero" = sin WorkflowCase, pero NO sin estado: persiste job + WorkflowDocument +
artefactos S3 con retención de N días (TBD) — por eso el job_id es reusable (re-extraer
o abrir caso sin re-OCR).
```

**Plano 2 — expediente** (Casos 1B, 2, 3):

```
POST /v1/cases                            crea/encuentra caso (external_ref, pipeline)
POST /v1/ingest/{token}                   archivos al caso (ya existe; + caseId del spec)
POST /v1/cases/{id}/data                  ⬅ implementa el stub /v1/case: datos validados
                                            como documento virtual (doc_type, payload, actor)
GET  /v1/cases/{id}/completeness          qué falta (patrón Ocrolus)
POST /v1/cases/{id}/ready                 resuelve la pausa await_documents (patrón Heron);
                                          idempotente; con faltantes ⇒ 409 salvo force:true.
                                          Los casos data-only (sin await_documents) arrancan
                                          solos al recibir /data — no necesitan ready
POST /v1/tasks/{id}/resolve               ya existe (clarificación/aprobación M2M)
POST /v1/cases/{id}/corrections           corrección de campos sin re-OCR → re-evalúa reglas
GET  /v1/cases/{id}                       estado + timeline
GET  /v1/cases/{id}/output                output final validado contra output_schema
```

**Webhooks (checkpoint events)** sobre el outbox existente:
`case.created`, `document.extracted` (existe), `case.needs_clarification`, `case.needs_review`,
`case.review.completed`, `analysis_run.completed` (existe), `case.output.ready`, `case.failed`.
Firmas HMAC estilo Svix ya implementadas; `event_id` = clave de dedup.

### 4.5 Confianza y clarificación (la variante stateful — otros casos)

**Nota D2**: el Caso 1 queda FUERA de este mecanismo — ahí el loop lo gobierna el cliente y los
mismos ítems (`reason`, `signals`, `candidates`) viajan **inline** en la respuesta de
`POST /v1/extract`, sin `HumanTask` ni webhook. Lo que sigue aplica a recetas donde Doxiq gobierna
la clarificación (fase `await_clarification`, otras integraciones).

Estructura del `clarification request` (payload del webhook `case.needs_clarification` y del
`HumanTask` externo):

```json
{
  "caseId": "…", "taskId": "…",
  "items": [
    {"fieldPath": "medicamentos[0].dosis", "reason": "low_confidence",
     "parseConfidence": 0.31, "signals": ["multiple_possible_answers"],
     "candidates": ["50mg", "500mg"], "page": 1, "bbox": [..]},
    {"reason": "missing_document", "documentType": "receta"}
  ],
  "resolveUrl": "/v1/tasks/{taskId}/resolve", "expiresAt": "…"
}
```

Cada ítem se convierte 1:1 en una pregunta de WhatsApp del bot **del cliente** (Doxiq no es dueño del
canal — consenso de mercado §3.2.6). La respuesta entra por `tasks/resolve` (ya funcional) o
`corrections`, se registra `verified_by=external`, y **solo se re-evalúa downstream** (reglas), jamás re-OCR.

### 4.6 Revisión humana multinivel

- **`ActivationPolicy`** (JSONB versionada en el pipeline, patrón A2I):
  `{field_thresholds: {default: 0.75, "juez.nombre": 0.9}, blocking_rule_severities: ["BLOCKER"], sample_rate: 0.05, mode: "by_exception" | "mandatory"}`.
- **Stages secuenciales** (patrón Nanonets/Instabase): `review_l1` (pool: analistas Doxiq, mandatory u
  on-flag) → `review_l2` (pool: analistas del tenant). Invariante: **el caso no avanza con flags
  abiertos**; el nivel 2 solo ve campos no verificados por nivel 1 (verificación por campo, patrón Rossum).
- **Lock pesimista** por caso en revisión (Klippa), comentarios por caso (handoff), audit log por campo,
  re-evaluación automática de reglas tras cada corrección **antes** de permitir aprobar.
- **QA sampling** (Hyperscience): % de casos auto-aprobados auditados — mide al modelo y a cada analista;
  base del SLA estilo Ocrolus para el tier interno.

### 4.7 Tools de enriquecimiento (el diferenciador)

`ToolDefinition` sobre `ConnectionAccount` (provider `HTTP`, capability `LOOKUP` — enums ya existen):
URL template + auth (API key/HMAC/OAuth del cliente) + schemas I/O + retries/backoff + SSRF guard
(reusar el de source_webhooks). La fase `enrich` invoca la tool con inputs del caso
(`policy_id`, `pharmacy_id`, `@oficio.juzgado.nombre`), y el resultado se persiste como **documento
virtual** con slug (`@poliza`, `@juez_db`) disponible para reglas, output (`x-source`) y UI.
Ejecución condicional: `when: "juez.nombre.confidence < 0.7"` (predicados ya soportados, a endurecer).
**Defaults v1**: `retries=3` con backoff exponencial, timeout 10 s por llamada;
`on_failure: review | continue | fail` configurable por tool (default `review` ⇒ el caso pasa a
`NEEDS_REVIEW` en vez de romper las reglas que referencian el `@slug` ausente).

### 4.8 Versionado

- `PipelineVersion` inmutable ya existe — añadir **publish/draft** y "pin" del run (el run ya sella la
  versión al arrancar; registrar también versiones de doc-type schemas y compilaciones de reglas usadas).
- Export/import del pipeline completo como JSON (git-able, patrón Sensible) — ya hay import de
  doc-types y reglas; generalizar.

### 4.9 UI (simple de usar, flexible por debajo)

1. **Editor de pipeline** = stepper vertical de tarjetas de fase (la metáfora ya existe en
   `workflow-step-card` + `workflow-arrow`; `/pipelines` ya lista fases read-only). Añadir: CRUD +
   reorder (dnd-kit ya está), formulario por `kind` (reusar config-forms), editor de `when` con
   token-chips, publish/diff de versiones. **Sin canvas de nodos** — innecesario y contra el estilo near-flat.
2. **Bandeja de casos** cross-workflow con colas por estado/asignación (fusión de `cases-view` +
   `review-queue-view`), indicadores de antigüedad/SLA, filtros guardados.
3. **Inspection Bench** (el north star del DESIGN.md, literalmente): visor PDF/imagen con bboxes y
   tiers de confianza (✅ ya existe, 952 líneas) + data-pane sincronizado (✅ existe) **+ edición inline
   de campos** (🆕: inputs, aceptar/corregir por campo, auditoría), Tab solo entre pendientes, orden por
   confianza ascendente, panel de bloqueadores ("este caso está aquí porque…"), comentarios, lock.
   Variante restringida para el stage cliente (enforce de roles por workflow — guardados pero no aplicados hoy).

---

## 5. Caso 1 mapeado (farmacias / seguros)

**Plano A — extracción de la receta** (interacción 1):
sistema del cliente → `POST /v1/extract?mode=sync` (foto de receta manuscrita) → pipeline
`receta-extract@v1`: `extract_text(vlm)` → `extract_fields` → `assess` → respuesta con
medicamentos/dosis + dos confidences + señales + candidatos. El bot del cliente decide con
`parse_confidence` si pide re-foto y con `signals` qué preguntar al farmacéutico. *(Decisión D2 §8.1:
el loop lo gobierna el cliente; la variante stateful con `await_clarification` queda en el catálogo
para otros casos, fuera del camino crítico del Caso 1.)*

**Plano B — análisis de cobertura** (interacción 2):
`POST /v1/cases {pipeline: "cobertura-poliza", external_ref}` →
`POST /v1/cases/{id}/data {doc_type: "datos_validados", payload: {medicamentos[...], pharmacy_id, policy_id}}` →
**auto-start** (la receta no tiene `await_documents`; el caso data-only arranca al recibir los datos) →
pipeline: `enrich(tool: consulta_poliza)` ⇒ documento virtual `@poliza` →
`analyze` (reglas: `@datos_validados.medicamentos[*]` × `@poliza.coberturas` — scope colección;
`#vademecum` opcional para normalizar nombres de fármacos) → `output` (schema: lista
cubierto/no-cubierto + copagos) → `deliver` (webhook firmado al sistema del cliente).

**Lo que falta construir para este caso**: `POST /v1/extract` + `GET /v1/jobs/{id}` con resultado y
extractor `vlm` (plano A); `POST /v1/cases`, `cases/{id}/data` con documentos virtuales y los GET de
lectura `GET /v1/cases/{id}` / `GET /v1/cases/{id}/output` (plano B — del stub `/v1/case` actual solo
existe el eco); tools HTTP; fases `assess` y `analyze` encadenadas. La base — intérprete, webhooks
firmados, confianza bbox, API keys — ya está.

## 6. Casos 4 y 5 — los casos "express" (y otros que habilita)

Dos casos adicionales, deliberadamente simples, que prueban el punto central: **no requieren
ninguna pieza nueva propia** — son recetas cortas del mismo catálogo. Mapeo visual en
`product/plans/re-architecture/mockups/cases.html §05–§06`.

### 6.1 Caso 4 — Órdenes de compra multicanal (fabricante de helados)

**El caso**: los pedidos llegan por email, WhatsApp y llamada telefónica; hay que extraer productos
y cantidades de cada pedido y devolverlos por webhook.

**Receta** `pedidos-multicanal@v1` (straight-through, sin pausas ni expediente formal — un caso por pedido):
`ingest → extract_text(:ocr|:asr) → extract_fields → assess → analyze(:normaliza #catalogo) → output → deliver`

- **El canal solo cambia cómo llega el documento**: el email aporta el PDF adjunto o el cuerpo del
  correo; WhatsApp la foto o la nota de voz; la llamada su grabación. Todo converge en `ingest` y de
  ahí el pipeline es idéntico para los tres.
- **Audio**: la nota de voz / grabación entra como un documento más y `extract_text` usa el extractor
  `asr` — una entrada más del catálogo de Lambdas de E1, el contrato de la fase no cambia.
  Alternativa v1 sin `asr`: el transcript del sistema telefónico entra por `cases/{id}/data` como
  documento virtual.
- **Normalización de productos**: una regla `DERIVATION` con `#catalogo` (KB) dentro de la fase
  `analyze` mapea "choco crujiente x12" → SKU. Precisión importante: los refs `#kb` hoy **solo se
  resuelven en el motor de reglas** (`refs.py` + `KBDocumentResolver`), no en `extract_fields` — por
  eso la receta lleva `analyze`. `assess` marca los ítems dudosos (la nota de voz con ruido cae a
  confianza baja) y el webhook expone la confianza **por ítem** — el ERP del fabricante decide qué
  confirma directo y qué verifica con su cliente.
- **Cuándo funciona**: por API desde **E3** (el sistema del cliente reenvía adjunto/foto/audio por
  `/v1/ingest`); los canales nativos email/WhatsApp y el extractor `asr` llegan en **E6**.

### 6.2 Caso 5 — CV contra puesto (RRHH)

**El caso**: llegan CVs en PDF; extraerlos con estructura; evaluar con reglas cuánto coincide el
candidato con un puesto; responder la estructura de match.

**Receta** `cv-vs-puesto@v1`:
`ingest → extract_text → extract_fields` + `cases/{id}/data(@puesto)` → `analyze(:derivation) → output → deliver`

- **El puesto es un documento más**: el perfil de la vacante entra como documento virtual `@puesto`
  por caso (cambiar de vacante no toca el pipeline — solo los datos; el mismo CV × N puestos = N
  casos baratos reutilizando el `job_id` sin re-OCR), o como `#puestos` en la KB si el puesto es
  fijo por workflow.
- **Las reglas `DERIVATION` ya existen y son exactamente esto**: reglas que *calculan* un valor —
  score por dimensión (`@puesto.requisitos × @cv.experiencia`, cobertura de skills, años mínimos,
  educación) — en vez de solo aprobar/fallar. El verdict agregado y el `confidence_score` del
  summary ya están construidos.
- **Output** contra `output_schema`: `{matchScore, dimensiones, fortalezas[], brechas[], veredicto}`
  con provenance por campo (citations a las reglas y a los campos del CV).
- **Cuándo funciona**: variante `#puestos` (KB) desde **E2** (solo necesita el encadenado
  analyze/output/deliver); variante `@puesto` por caso desde **E3** (necesita `cases/data`).
  Sin revisión humana, sin fan-out, sin tools.

### 6.3 Otros casos similares que habilita

- **Onboarding KYC / apertura de cuentas**: expediente con completitud (cédula + comprobante +
  formulario), reglas de paridad, revisión L1/L2.
- **Cuentas por pagar con 3-way match**: factura + OC + remisión; tool `enrich` contra el ERP.
- **Siniestros de seguros**: fotos + formularios por WhatsApp del asegurado, clarificación
  estructurada, reglas de póliza vía tool.
- **Autorizaciones médicas previas**: receta + historia + tabla de cobertura (KB), output
  aprobado/observado.
- **Underwriting de crédito PyME** (patrón Ocrolus/Heron): estados de cuenta multi-mes, agregados de
  nivel caso como reglas `DERIVATION`.
- **Licitaciones / contratos**: split de paquetes grandes, extracción por sección, reglas de
  cumplimiento contra KB normativa.

## 7. Plan de migración (etapas incrementales, cada una shippeable)

| Etapa | Contenido | Desbloquea |
|---|---|---|
| **E1 — Un solo motor** | Upload normal → intérprete con receta `standard@v1` (binding `workflows.pipeline_id`, seed por migración); **cutover directo del legacy** (D4 — no hay nada en producción; suite de regresión con fixtures, paridad campo a campo, y se eliminan `DocumentSetProcessingWorkflow` + el workflow de re-extracción, que se reimplementa como run extract-only sobre artefactos); catálogo `phase_kind → Lambda` versionada con pin por run (extractor seleccionable); `GET /v1/jobs/{id}` con resultado + `POST /v1/extract` async-first con `mode=sync` ≤5 págs (D1; en E1 solo `parse_confidence`); generalizar `PipelineState` a artefactos | Paridad + API M2M útil |
| **E2 — Encadenar el final** | Fases `analyze` (child workflow, D3), `output`, `deliver`; eventos `case.output.ready`/`case.failed`; **desacoplar `DocumentType` a catálogo org-level con schema versionado** (D6 — migración trivial sin datos en prod; elimina `default_schemas`/`per_doc_schema`/`doc_type_catalog` de `WorkflowORM`) | Pipelines end-to-end sin intervención |
| **E3 — Datos y tools** | `POST /v1/cases` (+ evento `case.created`) y GET de lectura `cases/{id}` / `cases/{id}/output`; `cases/{id}/data` (documentos virtuales, **auto-start** para casos data-only); `tool_definitions` + enrich HTTP firmado (defaults §4.7); fase `assess` (máx 3 candidates, solo con `multiple_possible_answers`); extractor `vlm` para manuscritos | **Caso 1 completo** (+ **Caso 5** completo y **Caso 4** vía API) |
| **E4 — Expediente formal** | CompletenessPolicy + `ready`/auto-ready + completeness endpoint; `confidence_gate` → evaluador de **ActivationPolicy** (columnas `activation_policy`/`completeness_policy` en `pipeline_versions`); `extract_fields` por documento (prerequisito de "cada doc se procesa al llegar"); gate de aprobación (`human_review` approval — rechazo ⇒ caso `REJECTED` sin deliver); estados públicos del caso (tabla de transiciones + migración del enum actual: DRAFT→RECEIVING, IN_PROGRESS→PROCESSING, ARCHIVED se conserva); upgrade `await_clarification` + eventos `case.needs_review`/`case.needs_clarification`; **diseño + ADR de la consola staff (D7, sin código)** | **Caso 2 completo** |
| **E5 — Fan-out y revisión 2 niveles** | `split_classify` con `fan_out: child_cases` (child workflows + lineage; el padre permanece `PROCESSING` y expone `children {total, por_estado}`); checksums país (CI para persona natural / NIT para empresa — regla condicional por `when` sobre el tipo de entidad); stages L1/L2 + verificación por campo + lock + evento `case.review.completed`; `corrections` (señal al run pausado → re-analyze como child, todas las reglas del caso en v1); **edición de campos en Inspection Bench**; matriz rol×acción + enforce de roles (primero, antes de la bandeja L2); **consola staff cross-tenant** para la cola L1 de analistas Llamitai (D7) | **Caso 3 completo** |
| **E6 — Pulido de plataforma** | Editor visual de pipelines, ActivationPolicy UI, QA sampling, export/import git-able, catálogo de plantillas; canales nativos de ingesta (source email + WhatsApp Business) y extractor `asr` — cierra el multicanal del **Caso 4** | Self-service |

> Desglose por componente de cada etapa — archivos a cambiar, qué se agrega (modelos, migraciones,
> endpoints, fases) y qué cambia en la UI — en `product/plans/re-architecture/mockups/cases.html §07`.

## 8. Decisiones zanjadas y riesgos

### 8.1 Decisiones zanjadas (2026-06-09)

| # | Decisión | Resolución | Implicaciones |
|---|---|---|---|
| **D1** | API de extracción (Caso 1A) | **Async-first + sync limitado**: `POST /v1/extract?mode=sync` solo ≤5 páginas (timeout ~30 s); el resto 202 + `GET /v1/jobs/{id}` **con resultado**; webhook opcional. Timeout o >5 págs con sync ⇒ **degrada a 202 + job_id, nunca error** (páginas contadas en el parse inicial) | El caso receta (1 página) vive en sync; un solo pipeline detrás de ambos modos |
| **D2** | Loop de clarificación (Caso 1) | **El cliente gobierna**: Doxiq responde extracción + confianza (2 capas) + señales + candidatos y termina; los datos validados entran por `POST /v1/cases/{id}/data` | `await_clarification` queda en el catálogo para otros casos, fuera del camino crítico del Caso 1 |
| **D3** | Ejecución de la fase `analyze` | **Child workflow**: el intérprete arranca `WorkflowAnalysisRunWorkflow` y espera | Conserva fan-out/SSE/cancel sin duplicación; estrena los child workflows que el split del Caso 3 reutiliza |
| **D4** | Retiro del motor legacy | **Cutover directo** — no hay nada en producción: suite de regresión con fixtures y se eliminan `DocumentSetProcessingWorkflow` + `DocumentSetFieldReExtractionWorkflow` en E1 | Sin flags ni shadow runs; congelar features sobre el legacy desde ya |
| **D5** | Ubicación de las policies | **En `PipelineVersion`**: ActivationPolicy y CompletenessPolicy son parte de la receta inmutable; el run sella la versión exacta | UI de «duplicar y publicar» para que tunear umbrales sea barato |
| **D6** | Catálogo de DocumentType | ~~Desacoplar a org-level~~ **AMENDADA (2026-06-10, Vic): workflow-scoped + versionado** — los doc-types siguen atados a su workflow (aislamiento por defecto); E2 añade `document_type_versions` inmutable + sellado de versión por run + recompilación/STALE de reglas al cambiar schema; se eliminan `default_schemas`/`per_doc_schema`/`doc_type_catalog` de `WorkflowORM` | Cero cambio de UX; si algún día se necesita catálogo org, la migración será más cara con runs sellados |
| **D7** | Acceso de analistas internos (cola L1) | **Consola staff cross-tenant**: superficie interna de Llamitai con la cola unificada de tareas L1 de todos los tenants | Requiere un concepto nuevo de autorización staff (rol de plataforma + audit por tenant) — el ítem nuevo más grande del plan; diseñarlo antes de E5 para no bloquear el Caso 3 |

Pendiente de confirmar **con el cliente** (no es decisión nuestra): el posible 4º tipo de documento
del Caso 2 — la CompletenessPolicy lo absorbe como una entrada más en `required_types`.

> Formalizar D1–D7 como ADRs (plugin `adr-writer`) cuando arranque la implementación.

### 8.2 Riesgos vigilados

- **Límite 2 MiB de Temporal**: el mapa de artefactos debe ser refs S3 siempre (ya se hace en
  `read_classified_refs`; convertirlo en regla del runtime).
- **Fan-out de Caso 3**: cientos de personas por oficio ⇒ presión sobre `EVAL_CONCURRENCY` y costo
  LLM; presupuestar por caso y paralelizar por child workflow, no por activity gigante.
- **Documentos virtuales en webhooks/UI**: filtrar por `source` donde solo se esperen archivos.
- **Enforce de roles por workflow** (guardados, no aplicados) es prerequisito del stage cliente L2 (E5).
- **Consola staff (D7)**: definir el modelo de permisos cross-tenant antes de E5; mientras no exista,
  fallback temporal = invitar analistas como miembros del tenant.

---

*Fuentes de investigación: docs.extend.ai, docs.reducto.ai, knowledge-base.rossum.ai,
help.hyperscience.com + flows-sdk.hyperscience.ai, docs.instabase.com, abbyy.com/vantage,
learn.microsoft.com (Document Intelligence / Content Understanding), AWS GenAI IDP Accelerator
(github.com/aws-solutions-library-samples), docs.unstructured.io, docs.sensible.so,
support.docsumo.com, docs.nanonets.com, klippa.com/dochorizon, docs.aws.amazon.com (A2I),
docs.ocrolus.com, docs.herondata.io, cascading.ai.*
