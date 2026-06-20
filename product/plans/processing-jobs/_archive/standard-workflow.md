---
feature: processing-jobs
type: plan
status: obsolete
coverage: 20
audited: 2026-06-16
superseded_by: backend DDD re-arch (ver docs/backend/)
---

# Plan: Documentos en Workflows STANDARD (con unificación de `WorkflowDocumentSet`)

> Ruta objetivo: `/workflows/[wf_slug]/documents`
> **Decisión clave**: en lugar de crear un modelo paralelo, **unificamos** `ProcessingJob` (existente, ANALYSIS) y el nuevo concepto de procesamiento STANDARD bajo una sola entidad `WorkflowDocumentSet` con `workflow_case_id` opcional. Una tabla, un workflow Temporal, un canal SSE, un hook de frontend.

---

## 1. Decisiones de arquitectura

### 1.1 Botón reutilizable

`frontend/src/presentation/workflows/cases/upload-button.tsx` se promueve a componente compartido. Como ahora el endpoint de dispatch también es único (ver §2.2), el botón sabe llamarlo directo.

- **Mover a:** `frontend/src/presentation/workflows/shared/document-upload-button.tsx`
- **Props:**
  ```ts
  interface DocumentUploadButtonProps {
    workflowId: string;
    workflowCaseId?: string;                  // ANALYSIS lo pasa, STANDARD no
    onDispatched?: (setId: string) => void;
    disabled?: boolean;
    label?: string;                           // default: "Cargar documento"
    accept?: string;                          // default: pdf/jpg/png
  }
  ```
- Internamente: `POST /v1/documents/upload` (existente, devuelve `fileId`) → `POST /v1/workflows/{wf}/document-sets` con `{fileId, workflowCaseId?}`.

### 1.2 Unificación: `ProcessingJob` → `WorkflowDocumentSet`

La tabla actual `processing_jobs` (ORM `ProcessingJobORM`) ya tiene `workflow_id`, `case_id`, `file_id`, `status`, `attempts`, `current_step`, `last_seq`, `error`, `result_summary`, `extracted_text`, `classified_pages`. El cambio es **conceptual + nombre**, no estructura de datos.

**Renombrar y relajar:**
- Tabla: `processing_jobs` → `workflow_document_sets`
- Columna `case_id`: **NOT NULL → NULL** (renombrada a `workflow_case_id` para alinear con `WorkflowDocumentORM`)
- Columna `job_id` (varchar único): se mantiene como ID de workflow Temporal para idempotencia. Renombrar a `temporal_workflow_id` para claridad.
- Índices renombrados; FK names regenerados por Alembic.

**Entidad de dominio (`WorkflowDocumentSet`):** completar el Pydantic actual (`ProcessingJob`) que solo expone `uuid, job_id, tenant_id, workflow_id, case_id, file_id, status, attempts, error, result_summary, created_at, updated_at`. Agregar los campos que hoy solo viven en el ORM: `current_step: str | None`, `last_seq: int = 0`, `extracted_text: str | None`, `classified_pages: str | None`. Renombrar `job_id` → `temporal_workflow_id` y `case_id` → `workflow_case_id: UUID | None`.

**Repo:** `ProcessingJobRepository` → `WorkflowDocumentSetRepository`. Se actualizan todas las referencias en código (use cases, repos, builders, presenters, activities Temporal).

**Distinción semántica conservada:**
- `WorkflowDocumentSet` = una corrida de procesamiento (1 upload → 1 set).
- `WorkflowDocument` (existente) = los documentos resultantes (clasificados) producidos por un set. ANALYSIS produce N por set; STANDARD típicamente 1.

**Cambios en `WorkflowDocumentORM`** (archivo actualmente mal nombrado `src/common/database/models/workspace_document.py` — se renombra a `workflow_document.py` en la misma PR para consistencia con el nombre de la clase):
- `workflow_case_id` ya es `UUID | None` (FK a `workflow_cases`, `ondelete=SET NULL`). Se mantiene.
- **Nuevo:** `document_set_id: UUID | None` (FK a `workflow_document_sets`, `ondelete=SET NULL`). Nullable porque hay documentos cargados manualmente sin pasar por el pipeline.
- Backfill en la migración: poblar `document_set_id` desde el `processing_jobs.uuid` que originó cada documento clasificado cuando el join sea derivable; dejar NULL para los SINGLE-source que nunca tuvieron job.

### 1.3 Temporal: un solo workflow

Adiós a la idea de "workflows hermanos". Con la unificación tenemos **un único** `@workflow.defn`:

```
backend/src/workflows/presentation/workflows/
├── pipeline.py                         # NEW: run_extraction_pipeline() helper deterministic
├── document_set_processing.py          # renombrado desde document_processing.py
└── activities/                         # se mantiene; archivos renombrados (ver §2.3)
```

`DocumentSetProcessingWorkflow` recibe input `DocumentSetInput(set_id, tenant_id, workflow_id, file_id, file_s3_key, workflow_case_id: UUID | None)` y delega toda la orquestación a `run_extraction_pipeline`. La activity `persist_classified_documents` no cambia funcionalmente — solo varía que ahora cada `WorkflowDocument` creado recibe `document_set_id` (siempre) y `workflow_case_id` (puede ser null).

`pipeline.py` aloja la corutina `run_extraction_pipeline()` (no decorada, solo `await` actividades → mantiene determinismo) que orquesta: `text_extract` → `classify_pages` → **`persist_classified_documents`** (entre clasificación y extracción) → `extract_fields` → `validate_fields`, intercalando `update_set_status` + `publish_set_event` por paso. Queda libre por si en el futuro nace un tercer caller.

### 1.4 SSE unificado

Un solo canal y endpoint, filtrable por `workflowCaseId`. **Sin compatibilidad legacy**: el endpoint `GET /v1/workflows/{wf}/cases/{case}/events` y el canal `case:{case_id}:events` se eliminan en la misma PR junto con la migración del frontend.

- **Canal Redis:** `workflow:{workflow_id}:document_sets:events`
- **Endpoint único:** `GET /v1/workflows/{wf}/document-sets/events?since_seq={n}&workflowCaseId={cid?}`
  - Sin `workflowCaseId` → todos los sets del workflow (vista STANDARD).
  - Con `workflowCaseId` → solo sets de ese case (vista case detail ANALYSIS).
- **Replay** desde `workflow_document_sets` aplicando el mismo filtro.

Eventos renombrados a un namespace único: `document_set.dispatched`, `document_set.step_started`, `document_set.step_completed`, `document_set.completed`, `document_set.failed`, `document_set.document_persisted` (uno por cada `WorkflowDocument` creado).

---

## 2. Backend: tareas

### 2.1 Renombrado del modelo

| Archivo | Acción |
|---------|--------|
| `src/common/database/models/processing_job.py` | Renombrar a `workflow_document_set.py`. Clase `ProcessingJobORM` → `WorkflowDocumentSetORM`. `__tablename__ = "workflow_document_sets"`. Renombrar `case_id` → `workflow_case_id` y volverlo nullable. Renombrar `job_id` → `temporal_workflow_id`. |
| `src/common/domain/models/processing_job.py` | Renombrar a `workflow_document_set.py`. `ProcessingJob` → `WorkflowDocumentSet`. Agregar al Pydantic los campos faltantes (`current_step: str \| None`, `last_seq: int = 0`, `extracted_text: str \| None`, `classified_pages: str \| None`). `workflow_case_id: UUID \| None`, `temporal_workflow_id: str`. |
| `src/common/database/models/workspace_document.py` | Renombrar archivo a `workflow_document.py` (la clase `WorkflowDocumentORM` ya existe; solo se cambia el path). Agregar columna `document_set_id: UUID \| None` con FK a `workflow_document_sets.uuid` `ondelete=SET NULL`. Mantener `workflow_case_id` nullable. Actualizar imports en los 18 sitios que referencian `workspace_document`. |
| `src/workflows/domain/repositories/processing_job_repository.py` | Renombrar a `workflow_document_set_repository.py`. ABC `WorkflowDocumentSetRepository`. Métodos: `find_by_id`, `list_by_workflow(workflow_id, workflow_case_id?: UUID, pagination)`, `create`, `claim`, `update_status`, `mark_done`, `mark_failed`. |
| `src/workflows/infrastructure/repositories/sql_processing_job.py` | Renombrar a `sql_workflow_document_set.py`. Mantener atomicidad (`SELECT FOR UPDATE SKIP LOCKED`, `WHERE` guards en `mark_*`). |
| `src/workflows/infrastructure/builders/processing_job.py` (si existe) | Renombrar análogo. |
| `src/common/database/versions/20260430.HHMMSS_<hash>_rename_processing_jobs_to_workflow_document_sets.py` | NEW migración: `ALTER TABLE processing_jobs RENAME TO workflow_document_sets`, `ALTER COLUMN case_id RENAME TO workflow_case_id` + `DROP NOT NULL`, `RENAME COLUMN job_id TO temporal_workflow_id`, renombrar índices/FKs. Sobre `workflow_documents`: `ADD COLUMN document_set_id UUID NULL` + FK + backfill desde `workflow_document_sets.uuid` cuando sea derivable por join. Downgrade reversible. |
| Todo el resto del código | Buscar y reemplazar `ProcessingJob` → `WorkflowDocumentSet`, `processing_job_repository` → `workflow_document_set_repository`, `case_id` → `workflow_case_id` (en el contexto del set), `workspace_document` → `workflow_document`. Corregir imports. |

### 2.2 Endpoint unificado de dispatch

El módulo destino es `application/document_processing/` (mantener el nombre — alberga `runner.py`, `input_builder.py` y otros helpers que siguen vigentes). El nuevo dispatcher absorbe la lógica de `extraction_starter.py`, que se elimina.

| Archivo | Contenido |
|---------|-----------|
| `src/workflows/application/document_processing/dispatcher.py` | `WorkflowDocumentSetDispatcher` use case: recibe `tenant_id, workflow_id, file_id, workflow_case_id?: UUID`. Valida workflow existe; si `workflow_case_id` provisto, valida que pertenece al workflow y que `workflow.workflow_type == "ANALYSIS"`; si es STANDARD rechaza con 409 cuando llega `workflow_case_id`. Crea set con `status=pending` y `temporal_workflow_id=str(set.uuid)`. Arranca `DocumentSetProcessingWorkflow` con ese ID (idempotencia). |
| `src/workflows/application/document_processing/extraction_starter.py` | **Eliminar.** Sus llamadores (solo `workflow_case_extraction.py`) se borran en esta misma PR. La lógica de armado del input Temporal vive en el dispatcher reutilizando `input_builder.py`. |
| `src/workflows/presentation/endpoints/workflow_document_sets.py` | `POST /v1/workflows/{wf}/document-sets` body `{fileId, workflowCaseId?}` → 202 `{setId, status: "dispatched"}`. <br> `GET /v1/workflows/{wf}/document-sets?workflowCaseId=…&page=…` → lista paginada. <br> `GET /v1/workflows/{wf}/document-sets/events?since_seq=&workflowCaseId=` → SSE. |
| `src/workflows/presentation/presenters/workflow_document_set.py` | camelCase: `setId, fileId, workflowCaseId, status, currentStep, lastSeq, error, resultSummary, createdAt, updatedAt`. |
| `src/workflows/presentation/endpoints/workflow_case_extraction.py` | **Eliminar** (su flujo lo absorbe el nuevo endpoint `POST /v1/workflows/{wf}/document-sets`). Quitar imports en `router.py`. |

Registrar nuevo router en `src/workflows/presentation/router.py` y eliminar la referencia a `start_case_file_extraction`.

### 2.3 Temporal

| Archivo | Acción |
|---------|--------|
| `src/workflows/presentation/workflows/pipeline.py` | NEW: `async def run_extraction_pipeline(input: PipelineInput, seq: SeqCounter) -> ExtractionResult`. Encadena los 4 lambdas + `update_set_status` + `publish_set_event` por paso. |
| `src/workflows/presentation/workflows/document_set_processing.py` | Renombrado desde `document_processing.py`. Clase `DocumentSetProcessingWorkflow`. Input incluye `workflow_case_id: UUID \| None`. Delega toda la orquestación a `run_extraction_pipeline` (que internamente intercala `persist_classified_documents` entre `classify_pages` y `extract_fields`). Actualizar `PUBLISH_CASE_EVENT_ACTIVITY` → `PUBLISH_DOCUMENT_SET_EVENT_ACTIVITY` y demás constantes. |
| `src/workflows/presentation/workflows/activities/update_processing_job_status.py` | Renombrar a `update_document_set_status.py`. |
| `src/workflows/presentation/workflows/activities/case_event_inputs.py` | Renombrar a `document_set_event_inputs.py`. Renombrar `PersistClassifiedDocumentsInput.processing_job_uuid` → `document_set_uuid` y `case_id` → `workflow_case_id`. |
| `src/common/infrastructure/temporal/activities/publish_event.py` | Renombrar a `publish_document_set_event.py`. Activity `@activity.defn(name="publish_case_event")` → `@activity.defn(name="publish_document_set_event")`. Publica al canal `workflow:{wf}:document_sets:events` con payload incluyendo `workflowCaseId` (o null) para filtrado server-side. |
| `src/workflows/presentation/workflows/activities/persist_classified_documents.py` | Sigue creando `workflow_documents` rows. Cada row recibe `document_set_id` y `workflow_case_id` (este último puede ser null). |
| `src/workflows/domain/events.py` | Reemplazar `case_channel(case_id)` por `document_set_channel(workflow_id)`. Eliminar la entidad `CaseEvent`/`CaseEventType` legacy y crear `DocumentSetEvent` con los nuevos tipos del §1.4. |
| `run_worker.py` | Actualizar imports tras renombrado; asegurar registro del workflow y todas las activities con sus nuevos nombres. |

### 2.4 SSE

`stream_document_set_events` (reemplaza por completo a `stream_case_events`; eliminar `src/workflows/presentation/endpoints/workflow_case_events.py` y su entrada en `router.py`):
1. Lee query params `since_seq`, `workflowCaseId?`.
2. Replay desde `workflow_document_sets` filtrado por `tenant_id` + `workflow_id` (+ `workflow_case_id` si presente) con `last_seq > since_seq`. Replay también desde `workflow_documents` para emitir `document_set.document_persisted` por cada doc cuyo `document_set_id` esté en el rango.
3. Suscribe al canal Redis `workflow:{wf}:document_sets:events` y filtra por `workflowCaseId` en el handler antes de forwardear al cliente.
4. Heartbeat 20s, formato `event: <type>\ndata: <json>`, `seq` monotónico por set.

---

## 3. Frontend: tareas

### 3.1 Componente compartido

- **Crear:** `src/presentation/workflows/shared/document-upload-button.tsx` (mover desde `cases/upload-button.tsx`, props como en §1.1, llama directo al endpoint unificado).
- **Actualizar:** `case-detail-view.tsx` — pasa `workflowId` y `workflowCaseId`; el `onDispatched(setId)` invalida queries y deja que SSE actualice.
- **Eliminar:** `cases/upload-button.tsx`.

### 3.2 Domain + infrastructure

| Archivo | Acción |
|---------|--------|
| `src/domain/entities/workflow-document-set.ts` | NEW. Tipo `WorkflowDocumentSet` (espejo del presenter). |
| `src/domain/events/document-set-event.ts` | NEW. `DocumentSetEventEnvelope` y enum de tipos. |
| `src/domain/entities/processing-job.ts` (si existe) | Eliminar; reemplazar referencias. |
| `src/domain/repositories/workflow-document-set-repository.ts` | NEW. Interface con `dispatch({workflowId, fileId, workflowCaseId?})`, `list({workflowId, workflowCaseId?, page})`. |
| `src/infrastructure/repositories/http-workflow-document-set.ts` | NEW. Implementación contra los nuevos endpoints. |
| `src/infrastructure/repositories/http-case.ts` | Quitar la llamada actual a `/v1/workflows/{wf}/cases/{case}/files/{file}/extract` y reemplazarla por el dispatcher unificado. |
| `src/infrastructure/http/sse.ts` | Sin cambios; reutilizar `subscribeSSE()`. |

### 3.3 Hook unificado

- **Crear:** `src/application/hooks/use-document-set-events.ts` con firma `useDocumentSetEvents({ workflowId, workflowCaseId? })`. Reducer:
  - `Map<setId, SetView>` (status, currentStep, progress, error, lastSeq).
  - `Map<documentId, DocumentView>` derivado de eventos `document_set.document_persisted`.
  - Manejo de reconexión con `since_seq=lastSeq`.
- **Eliminar:** `use-case-events.ts`, `use-case-events.test.tsx`, `use-case-events.reducer.test.ts`. La vista de case detail pasa a consumir `useDocumentSetEvents({ workflowId, workflowCaseId })`.

### 3.4 Vistas

- **`src/presentation/workflows/documents/document-sets-view.tsx`** (STANDARD)
  - Reemplazar `<Input type="file">` por `<DocumentUploadButton workflowId={...} onDispatched={onDispatched} />`.
  - `onDispatched(setId)` → optimistic insert en la tabla con `status=pending`; SSE actualiza el resto.
  - Conectar `useDocumentSetEvents({ workflowId })`.
  - Mergear estado live (sets en progreso) con la query histórica de `workflow-documents-store`.

- **`src/presentation/workflows/cases/case-detail-view.tsx`** (ANALYSIS)
  - Migrar a `useDocumentSetEvents({ workflowId, workflowCaseId })` apuntando directo al endpoint nuevo.
  - Adaptar `LiveFeedBottomPanel` al nuevo payload (`document_set.*` en lugar de `JOB_*`/`document.*`).

- **Crear:** `src/presentation/workflows/shared/document-set-status-badge.tsx` con badge + barra de progreso, reutilizado por la tabla STANDARD y el feed de cases.

---

## 4. Orden de implementación

Como no hay producción que mantener compatible, todo va en una sola PR coordinada (back + front + worker) sin alias intermedios.

1. **Backend rename + migración SQL**: tabla `processing_jobs` → `workflow_document_sets` (con `case_id` → `workflow_case_id` nullable, `job_id` → `temporal_workflow_id`); columna `document_set_id` en `workflow_documents`; rename de archivo `workspace_document.py` → `workflow_document.py`. ORM, entity (con campos completos), repo, builder, imports en los 18 sitios.
2. **Backend: dispatcher + endpoint unificado + presenter** en `application/document_processing/dispatcher.py`. Borrar `workflow_case_extraction.py` y su entrada del router.
3. **Backend: rename del Temporal workflow** + extraer `pipeline.py` + renombrar todas las activities (incluyendo `publish_event.py` en `common/infrastructure/temporal/activities/`). Actualizar `run_worker.py`.
4. **Backend: SSE unificado** con filtro por `workflowCaseId`. Borrar `workflow_case_events.py` y la entidad `CaseEvent`/`CaseEventType`.
5. **Frontend: extraer `DocumentUploadButton`** y hook `useDocumentSetEvents`. Borrar `use-case-events.ts` y sus tests. Migrar `case-detail-view.tsx` al nuevo hook + endpoint.
6. **Frontend: documents-view standard** con botón + dispatcher + hook + tabla live.
7. **QA end-to-end**: upload en ambos modos (con y sin `workflowCaseId`), validar progreso step-by-step, persistencia de `WorkflowDocument` rows con `document_set_id`, completed con resumen.

---

## 5. Riesgos / preguntas abiertas

- **`WorkflowDocument.document_set_id` nullable**: queda nullable porque hay docs SINGLE creados sin pasar por el pipeline. El backfill en la misma migración solo cubre los que vinieron de un `processing_jobs` existente.
- **Tipo de workflow**: el campo es `Workflow.workflow_type: str` (default `"STANDARD"`) con enum `WorkflowType.{STANDARD, ANALYSIS}` en `src/common/domain/enums/workflows.py`. El dispatcher rechaza 409 si llega `workflowCaseId` a un workflow STANDARD; para ANALYSIS, `workflowCaseId` es obligatorio.
- **Idempotencia Temporal**: `temporal_workflow_id = str(set.uuid)` evita duplicados ante reintentos del cliente. Reemplaza la convención previa `build_job_id(...)` que se elimina junto con `extraction_starter`/`workflow_case_extraction`.
- **Renombrado masivo de imports**: una sola PR. Buscar también en tests, fixtures y el frontend (`/v1/workflows/{wf}/cases/{case}/files/{file}/extract`, `/v1/workflows/{wf}/cases/{case}/events`).
- **Activities cross-module**: `publish_event.py` vive en `common/infrastructure/temporal/activities/` (no bajo `workflows/`). Asegurar que tras el rename siga registrándose en `run_worker.py` desde su nueva ubicación o moverlo a `workflows/presentation/workflows/activities/` si conceptualmente cabe ahí.
