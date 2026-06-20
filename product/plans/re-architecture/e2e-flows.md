---
feature: re-architecture
type: plan
status: implemented
coverage: 85
audited: 2026-06-16
---

# Plan: Flujos End-to-End principales (base para E2E tests)

> Objetivo: identificar los 5 flujos E2E **principales** del producto para luego
> escribirlos como tests automatizados (Playwright en frontend / pytest E2E HTTP en
> backend). Cada flujo describe: **meta**, **precondiciones**, **pasos**, **aserciones**
> esperadas y **superficies** (rutas UI / endpoints / specs de referencia).
>
> Convención de tipos de workflow:
> - **STANDARD** → extracción de documentos. Trabaja directo sobre `/documents`.
> - **ANALYSIS** → produce `cases`, corre `AnalysisRule`s sobre datos extraídos.

---

## Flujo 1 — Onboarding y setup del workspace

**Meta:** un usuario nuevo entra al producto, queda dentro de un tenant y arma el equipo
con roles. Es el flujo de entrada que habilita todos los demás.

**Precondiciones:** instancia limpia (sin sesión); email de invitación capturable.

**Pasos:**
1. Registro / login (`/register`, `/login`) → cookies HttpOnly (access/refresh) emitidas
   por el BFF (`/api/auth/login`).
2. Resolución de tenant: usuario sin tenant cae en `/unassigned`; con tenant entra a
   `/dashboard`. Verificar `switch-tenant` si hay múltiples.
3. Invitar miembro desde `/members` → se genera invitación con token.
4. Aceptar invitación (`/invitations/[token]` → `/api/auth/invitations/[token]/accept`).
5. Asignar rol al miembro desde `/roles` / `/members`.

**Aserciones:**
- Sesión persiste tras refresh (refresh token rota correctamente).
- `TenantUser` creado con `first_name`/`last_name` por tenant (no en `User`).
- Miembro invitado aparece en la lista con el rol asignado.
- Rutas protegidas redirigen a login sin sesión; `/forbidden` cuando falta permiso.

**Superficies:** `product/plans/auth/frontend-auth.md`, `product/plans/auth/backend-auth.md`, `product/plans/tenants/switch-tenant.md`,
`product/specs/roles-permissions/roles-permission.md`. Rutas: `(public)/register|invitations|reset_password`,
`(protected)/members|roles|profile|settings`.

---

## Flujo 2 — Crear workflow STANDARD + configurar primer document type

> (El ejemplo dado por el usuario.)

**Meta:** crear un workflow tipo STANDARD y dejar configurado su primer document type:
ejemplo de documento + configuración de campos (`fields`) + reglas de validación.

**Precondiciones:** sesión activa con tenant y permiso de edición de workflows.

**Pasos:**
1. Crear workflow seleccionando tipo **STANDARD** → redirige a `/workflows/[wf_slug]`.
2. Ir a `document-types` y crear un document type (`name`, `slug`, `description`).
3. Subir **document example** (`sample_file_id`).
4. Configurar **`fields`** (JSON Schema del documento: nombres, tipos, requeridos).
5. Definir **`validation_rules`** a nivel campo (se ejecutan dentro del pipeline de
   extracción, no son cruce entre docs).
6. Guardar y verificar persistencia.

**Aserciones:**
- Workflow creado con `type = STANDARD`.
- `DocumentType` persistido con `fields` (JSON Schema válido) + `validation_rules` + `slug`
  (el `slug` lo usa el clasificador).
- `sample_file_id` referencia un archivo en storage.
- Reabrir la página rehidrata el form con la config guardada.

**Superficies:** `product/plans/processing-jobs/_archive/standard-workflow.md`, `product/specs/extraction/extra-fields.md`,
`product/plans/processing-jobs/workflow_persistence.md`. Modelo `document_type.py` (`fields`, `validation_rules`,
`slug`, `sample_file_id`). Rutas: `(protected)/workflows/[wf_slug]/document-types/[documentTypeId]`,
`(protected)/doctypes`.

---

## Flujo 3 — Ingesta de documento y pipeline de extracción (con feedback en vivo)

**Meta:** subir un documento al workflow y obtener datos estructurados extraídos,
siguiendo el progreso en tiempo real (SSE) mientras corre el pipeline de Temporal.

**Precondiciones:** workflow STANDARD con al menos un document type configurado (Flujo 2).

**Pasos:**
1. Subir archivo desde el botón compartido → `POST /v1/documents/upload` (devuelve `fileId`)
   → `POST /v1/workflows/{wf}/document-sets` (crea `WorkflowDocumentSet`).
2. Suscribirse al canal SSE del set y observar eventos: `job.*` (pre-clasificación) →
   `document.*` (post-clasificación).
3. Pipeline Temporal: `extract_text` (OCR) → `classify_pages` → `extract_fields` →
   `validate` → persiste N `WorkflowDocument`.
4. Ver el detalle del documento con los datos extraídos y el estado de validación.

**Aserciones:**
- `WorkflowDocumentSet` creado; un archivo por request (D5).
- `WorkflowDocument` persistido temprano tras `classify_pages` (los IDs reales viajan en
  los eventos desde el inicio — D3).
- Progreso continuo vía SSE (no salto directo a "completado").
- Error parcial: un documento que falla queda `failed` sin abortar el set (`status: partial` — D6).
- Datos extraídos cumplen el `fields` schema; `validation_rules` reflejadas en el resultado.

**Superficies:** `product/plans/sse-events/upload-document.md`, `product/plans/processing-jobs/_archive/standard-workflow.md`,
`product/plans/sse-events/sse-events.md`, `product/specs/processing-jobs/processing_workflow.md`, `product/plans/extraction/enriched_extraction.md`.
Rutas: `(protected)/workflows/[wf_slug]/documents/[documentId]`.

---

## Flujo 4 — Workflow ANALYSIS: reglas + ejecución de análisis sobre un case

**Meta:** sobre un workflow ANALYSIS, configurar knowledge base y analysis rules, armar un
case con documentos, disparar el análisis y obtener un `AnalysisRun` con resultados + reporte.

**Precondiciones:** workflow ANALYSIS con document types; documentos extraídos disponibles
(Flujo 3 aplicado al case).

**Pasos:**
1. Configurar **Knowledge Base** del workflow (`/knowledge`) — embeddings para `#kb_slug`.
2. Crear **AnalysisRule**s (`/analysis-rules`) usando la sintaxis de tokens:
   `@slug.path` (datos del case), `#kb_slug` (KB), `{{system_var}}` (runtime, ej. `{{now}}`).
3. Crear un **case** (`/cases`) y subir/asociar documentos (reusa Flujo 3 con `workflowCaseId`).
4. Disparar el análisis desde la UI del case → corre en background.
5. Seguir resultados por SSE; al cerrar se persiste `AnalysisRun` + N `AnalysisRuleResult`.
6. Ver el **reporte** de ejecución.

**Aserciones:**
- Reglas guardadas con tokens resueltos correctamente (las tres familias disjuntas).
- `AnalysisRun` creado con un `AnalysisRuleResult` por regla; trazabilidad del pipeline
  multi-etapa (pre-eval determinística → reviewer LLM → self-consistency → crítico → verificación).
- Streaming de resultados regla a regla vía SSE.
- Reporte refleja veredictos y evidencia por regla.

**Superficies:** `product/specs/analysis-rules/_archive/analysis-execution.md`, `product/plans/analysis-rules/_archive/analysis-execution.impl.md`,
`product/plans/analysis-rules/_archive/create-rules.md`, `product/plans/analysis-rules/_archive/analisis-rules.md`, `product/plans/analysis-rules/_archive/analysis-exec-report.md`,
`product/specs/knowledge-base/rag-flow.md`, `product/plans/case-output/case-output.md`. Rutas:
`(protected)/workflows/[wf_slug]/{analysis-rules,knowledge,cases,cases/[caseId],synthesis}`.

---

## Flujo 5 — Conexiones: ingesta por Origen + entrega por Destino

**Meta:** automatizar la entrada y salida de un workflow vía Conexiones — un **Origen**
(webhook entrante / email) que ingesta un documento y lo procesa, y un **Destino** (webhook)
que entrega el resultado del análisis.

**Precondiciones:** workflow configurado (Flujos 2–4); `ConnectionAccount` a nivel org
registrado.

**Pasos:**
1. En `/connections/sources`, crear un **Origen** webhook (con su secret/firma) bindeado al
   workflow.
2. Enviar un payload de prueba al endpoint de ingesta → se crea el documento y dispara el
   pipeline (reusa Flujo 3).
3. En `/connections/destinations/webhooks`, crear un **Destino** webhook bindeado a un evento
   (ej. `analysis_run.completed`).
4. Disparar un análisis (Flujo 4) y verificar la entrega al destino.

**Aserciones:**
- Verificación de firma del webhook entrante (Standard Webhooks).
- Documento ingestado queda asociado al workflow/case correcto.
- El destino recibe `analysis_run.completed` (resumen, sin eventos por-documento).
- Reintentos/estado de entrega visibles en la UI del destino.

> **Nota de estado (al 2026-06-08):** el registro org de `ConnectionAccount` está construido,
> pero **bindings/delivery** e **inbound-email/Slack** aún están pendientes/bloqueados; el spec de
> source webhooks está cerrado pero su implementación está pendiente. Este flujo es objetivo de
> E2E **una vez** que la entrega/ingesta esté implementada; mientras tanto, cubrir lo disponible
> (registro de cuentas, creación de bindings) y marcar el resto como `skip`/pendiente.

**Superficies:** `product/specs/connections/spec.md`, `product/specs/source-webhooks/_archive/spec.md`,
`product/specs/source-webhooks/standard-webhooks.md`, `product/plans/sse-events/_archive/sse-events-extern.md`. Rutas:
`(protected)/workflows/[wf_slug]/connections/{sources,destinations/webhooks/[destinationId]}`,
`(protected)/connections`. Memoria: `project_connections_feature`, `project_source_webhooks`,
`project_analysis_webhooks`.

---

## Notas para implementar los E2E tests

- **Frontend (Playwright):** entrar siempre por el BFF (`/api/...`), nunca al backend directo
  (regla MANDATORY de `CLAUDE.md`). Capturar cookies HttpOnly del login para el resto de los flujos.
- **Backend (pytest E2E):** usar fixtures de seed (`scripts/seed_test_user.py`,
  `scripts/seed_processes.py`) y la skill `python-testing` (expects, AAA, fixtures).
- **SSE:** los flujos 3 y 4 dependen de eventos en vivo — testear consumo de `EventSource`
  (snapshot/replay desde Postgres como fuente de verdad).
- **Temporal:** el pipeline corre en worker (`run_worker.py`); el E2E debe esperar la
  terminación del workflow (poll de estado del set/case o esperar evento de cierre).
- **Orden sugerido de dependencia:** 1 → 2 → 3 → 4 → 5 (cada flujo reusa artefactos del anterior).