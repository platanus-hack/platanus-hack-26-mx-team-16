---
feature: sse-events
type: plan
status: implemented
coverage: 85
audited: 2026-06-16
---

# Upload Document — Live Feedback Spec

> Flujo de carga de documentos en el detalle de un Case con feedback en tiempo
> real vía SSE durante el procesamiento del `DocumentProcessingWorkflow` de Temporal.

## 1. Contexto y objetivo

Cuando un usuario sube un archivo en el detalle de un Case:

1. El archivo (PDF, imagen) puede contener **N documentos lógicos** de distintos
   `document_type` (ej: 1 cédula, 1 póliza, 3 certificados médicos).
2. El `DocumentProcessingWorkflow` (Temporal) corre OCR + clasificación +
   extracción + validación, y termina creando N `WorkflowDocument` en la DB.
3. La UI del case debe mostrar **progreso continuo**, no esperar al final del
   workflow para refrescar.

El reto: los `WorkflowDocument` no existen hasta que el workflow clasifica el
archivo. La UI necesita feedback antes y después de ese momento, con
granularidad apropiada en cada fase.

## 2. Decisiones de diseño (resueltas)

| # | Decisión | Razón |
|---|---|---|
| D1 | **Bus de eventos híbrido**: Redis Pub/Sub para stream en vivo + Postgres como fuente de verdad persistente para snapshot/replay. | Desacopla la entrega de eventos de la DB principal, escala mejor y mantiene reconciliación trivial via PG. |
| D2 | **Eliminar `pg_notify`** del flujo de SSE; PG queda solo como tabla de estado (`processing_jobs`, `workflow_documents`). | Un solo bus de eventos. Menos sistemas que mantener. |
| D3 | **Persistir `WorkflowDocument` temprano**, justo después de `classify_pages`, dentro del workflow como Temporal Activity. | Los IDs reales viajan en los eventos desde el primer momento. Replay es leer PG, sin reconciliación. |
| D4 | **Modelo de eventos de dos niveles**: `job.*` antes de clasificar, `document.*` después. | Pre-clasificación solo existe el archivo; post-clasificación cada documento tiene su propio estado. |
| D5 | **Un archivo por request**. Múltiples archivos = múltiples llamadas al endpoint. | Simplifica el contrato del workflow y el modelo de eventos. |
| D6 | **Errores parciales: continuar**. Un documento que falla no aborta el job; se marca `failed` y los demás continúan. | Alineado con el `status: "partial"` del lambda. Mejor UX. |
| D7 | **Flag `persist=True` en input del workflow** para permitir correrlo standalone sin DB en debugging. | El usuario necesita poder ejecutar el workflow aislado para depurar lambdas/clasificación. |

## 3. Arquitectura

```
┌─────────┐  upload   ┌───────────────┐
│ Browser │──────────▶│ POST /files   │── S3
└─────────┘           └───────┬───────┘
     │                        │ file_id
     │                        ▼
     │  start          ┌──────────────────────────────────┐
     │────────────────▶│ POST /workflows/{wf}/cases/{c}/  │
     │ (file_id)       │       files/{file_id}/extract    │
     │                 └────────────┬─────────────────────┘
     │                              │ start_workflow
     │                              ▼
     │                ┌────────────────────────────────┐
     │                │  Temporal: DocumentProcessing  │
     │                │     Workflow                   │
     │                │                                │
     │                │  extract_text   ──┐            │
     │                │  classify_pages ──┤ checkpoints│
     │                │  persist_docs   ──┤  publish   │
     │                │  extract_fields ──┤            │
     │                │  validate       ──┘            │
     │                └─────┬──────────────┬───────────┘
     │                      │ writes       │ publish
     │                      ▼              ▼
     │              ┌──────────────┐  ┌──────────┐
     │              │ Postgres     │  │  Redis   │
     │              │ processing_  │  │ Pub/Sub  │
     │              │ jobs +       │  │ case:    │
     │              │ workflow_    │  │ {id}:    │
     │              │ documents    │  │ events   │
     │              └──────┬───────┘  └────┬─────┘
     │                     │               │
     │  GET snapshot       │  subscribe    │
     │◀────────────────────┘               │
     │  GET /events (SSE) ─────────────────┘
     │
     ▼
   UI (JobCard + DocumentCards en case detail)
```

## 4. Modelo de eventos

### 4.1 Enum

Ubicación: `backend/src/common/domain/enums/case_events.py`

```python
from enum import StrEnum

class CaseEventType(StrEnum):
    # Job-level (pre-classification y aggregate)
    JOB_STARTED            = "job.started"
    JOB_STEP_PROGRESS      = "job.step.progress"
    JOB_CLASSIFIED         = "job.classified"
    JOB_COMPLETED          = "job.completed"
    JOB_FAILED             = "job.failed"

    # Document-level (post-classification)
    DOCUMENT_STEP_STARTED  = "document.step.started"
    DOCUMENT_COMPLETED     = "document.completed"
    DOCUMENT_FAILED        = "document.failed"


class JobStep(StrEnum):
    EXTRACT_TEXT     = "extract_text"
    CLASSIFY_PAGES   = "classify_pages"
    PERSIST_DOCS     = "persist_documents"
    EXTRACT_FIELDS   = "extract_fields"
    VALIDATE         = "validate_extraction"


class JobStatus(StrEnum):
    PENDING     = "pending"
    PROCESSING  = "processing"
    COMPLETED   = "completed"
    PARTIAL     = "partial"   # algunos docs OK, otros fallaron
    FAILED      = "failed"


class DocumentStatus(StrEnum):
    PENDING     = "pending"
    EXTRACTING  = "extracting"
    VALIDATING  = "validating"
    COMPLETED   = "completed"
    FAILED      = "failed"
```

El frontend espeja este enum en `frontend/src/domain/events/case-events.ts`.

### 4.2 Envelope

Todos los eventos heredan de una base `Event` que define el canal de
publicación. El publisher es agnóstico al tipo de evento — sólo consulta
`event.channel`. Esto permite reusar el mismo publisher para otros dominios
(workflows, jobs, tenants, etc.) sin tocar la infra.

Ubicaciones:
- `Event` (base): `backend/src/common/domain/events/base.py`
- `CaseEvent`: `backend/src/workflows/domain/events.py`

```python
# common/domain/events/base.py
class Event(BaseModel):
    seq: int                      # monotónico por canal lógico
    ts: datetime                   # UTC
    payload: dict                  # shape específico por tipo

    @property
    def channel(self) -> str:
        raise NotImplementedError


# workflows/domain/events.py
class CaseEvent(Event):
    type: CaseEventType
    case_id: UUID
    job_id: UUID
    document_id: UUID | None = None

    @property
    def channel(self) -> str:
        return f"case:{self.case_id}:events"
```

### 4.3 Payloads por tipo

```python
# job.started
{ file_id, file_name, file_size, mime_type }

# job.step.progress
{ step: JobStep, pct: 0..100, message?: str }

# job.classified  (envelope.document_id = null)
{ documents: [
    { document_id, document_type_code, document_type_name,
      document_index, page_range: [from, to] }
]}

# document.step.started  (document_id viene en el envelope)
{ step: JobStep ("extract_fields"|"validate_extraction") }

# document.completed  (document_id viene en el envelope)
{ summary: { extracted_field_count, validation_pass_count,
             validation_fail_count } }

# document.failed  (document_id viene en el envelope)
{ error_code, message, source_step: JobStep }

# job.completed
{ status: JobStatus.COMPLETED|PARTIAL,
  document_ids: [...],
  failed_document_ids: [...] }

# job.failed
{ error_code, message, source_step?: JobStep }
```

### 4.4 Resolución de canales

El canal lo define cada evento vía la propiedad `channel` (ver 4.2). Para
`CaseEvent` es:

```
case:{case_id}:events
```

Pros: el frontend escucha un único canal por vista. Un usuario viendo un case
recibe eventos de todos los jobs activos en ese case (puede haber varios uploads
encolados en paralelo). El `job_id` en el envelope los desambigua.

Nuevos tipos de evento (e.g. `WorkflowEvent`, `JobEvent`) sólo necesitan
implementar su propia `channel` — el publisher e infra de SSE no cambian.

## 5. Modelo de datos (Postgres)

### 5.1 `processing_jobs` (existente — extender)

Añadir:

| Columna | Tipo | Notas |
|---|---|---|
| `case_id` | UUID FK | ya debe existir; verificar |
| `file_id` | UUID FK | el archivo origen |
| `status` | `JobStatus` | enum string |
| `current_step` | `JobStep` nullable | última fase reportada |
| `last_seq` | int | último `seq` publicado |
| `error` | jsonb nullable | si `status='failed'` |

### 5.2 `workflow_documents` (existente — extender)

| Columna | Tipo | Notas |
|---|---|---|
| `id` | UUID | generado por la activity al persistir; viaja en eventos desde `JOB_CLASSIFIED` |
| `case_id` | UUID FK | |
| `processing_job_id` | UUID FK | nuevo, nullable durante migración |
| `document_type_id` | UUID FK | |
| `document_index` | int | 0-based, posición dentro del archivo |
| `page_range` | jsonb `{from, to}` | rango de páginas en el archivo origen |
| `status` | `DocumentStatus` | |
| `extraction` | jsonb nullable | resultado de `extract_fields` |
| `validation` | jsonb nullable | resultado de `validate_extraction` |
| `error` | jsonb nullable | si `status='failed'` |

Migration: `backend/src/common/database/versions/{ts}_extend_processing_jobs_workflow_documents.py`

## 6. Backend — cambios concretos

### 6.1 Nuevo `EventPublisher` (Redis)

Ubicación: `backend/src/common/infrastructure/event_publisher.py`

Genérico: cualquier evento que herede de `Event` (ver 4.2) se publica en el
canal que él mismo expone. No conoce a `Case` ni a ningún dominio puntual.

```python
@dataclass
class RedisEventPublisher:
    redis: Redis

    async def publish(self, event: Event) -> None:
        await self.redis.publish(event.channel, event.model_dump_json())
```

Inyectado vía dependencias en endpoints; usado vía Activity en los workflows.
Reusable para cualquier futuro stream SSE (workflow events, job events, etc.).

### 6.2 Activity `persist_classified_documents`

Ubicación: `backend/src/workflows/presentation/workflows/activities/persist_classified_documents.py`

```python
@activity.defn
async def persist_classified_documents(
    payload: PersistClassifiedDocumentsInput,
) -> PersistClassifiedDocumentsOutput:
    """
    Idempotente. Crea N filas workflow_documents con status='extracting'.
    Devuelve los UUIDs reales para que el workflow los use en eventos.
    """
```

Input: `{ job_id, case_id, classify_pages_output }`
Output: `{ documents: [{document_id, document_type_id, document_index, page_range}] }`

### 6.3 Activity `publish_event`

Ubicación: `backend/src/common/infrastructure/temporal/activities/publish_event.py`

Genérica: vive en `common` para que cualquier Temporal workflow del proyecto
la pueda registrar y reusar. Wraps `RedisEventPublisher.publish` y acepta
cualquier `Event`. Llamada por `_checkpoint()` del workflow con un `CaseEvent`
ya construido. **Es Activity** (no llamada directa) porque: (a) Redis IO,
(b) reintentos automáticos si Redis está caído momentáneamente.

### 6.4 Activity `update_processing_job_status`

Actualiza `processing_jobs.{status, current_step, last_seq}` y
`workflow_documents.status` según corresponda. Llamada antes de cada publish
para que el snapshot esté siempre coherente con (o por delante de) el evento.

### 6.5 `DocumentProcessingWorkflow` — cambios

Input extendido:

```python
class DocumentProcessingInput(BaseModel):
    file_id: UUID
    case_id: UUID
    workflow_id: UUID
    job_id: UUID
    document_types: list[DocumentTypeRef]
    persist: bool = True   # D7: false en modo debugging standalone
```

Cuerpo (pseudo):

```
async def run(input):
    await self._checkpoint(JOB_STARTED, payload={file_id, file_name, ...})

    # Step 1
    await self._checkpoint(JOB_STEP_PROGRESS, step=EXTRACT_TEXT, pct=0)
    extract_text = await invoke_lambda("extract_text", ...)
    await self._checkpoint(JOB_STEP_PROGRESS, step=EXTRACT_TEXT, pct=100)

    # Step 2
    await self._checkpoint(JOB_STEP_PROGRESS, step=CLASSIFY_PAGES, pct=0)
    classify = await invoke_lambda("classify_pages", ...)
    await self._checkpoint(JOB_STEP_PROGRESS, step=CLASSIFY_PAGES, pct=100)

    # Step 3 — persistir y emitir job.classified
    if input.persist:
        persisted = await persist_classified_documents({...})
        documents = persisted.documents
    else:
        documents = synthesize_in_memory_refs(classify)  # UUIDs in-memory

    await self._checkpoint(JOB_CLASSIFIED, payload={"documents": documents})

    # Step 4 — extract_fields (fan-out interno en lambda)
    for doc in documents:
        await self._checkpoint(DOCUMENT_STEP_STARTED, document_id=doc.id,
                               step=EXTRACT_FIELDS)

    extract = await invoke_lambda("extract_fields", ...)
    # extract.errors[] y extract.extractions[] vienen indexados por document_index

    # Mapear extractions y errores a workflow_documents
    for doc in documents:
        result = extract.find(doc.document_index)
        if result.is_error:
            if input.persist:
                await mark_document_failed(doc.id, result.error)
            await self._checkpoint(DOCUMENT_FAILED, document_id=doc.id,
                                   payload={...})
        # los exitosos siguen al step de validate

    # Step 5 — validate_extraction
    survivors = [d for d in documents if not d.failed]
    for doc in survivors:
        await self._checkpoint(DOCUMENT_STEP_STARTED, document_id=doc.id,
                               step=VALIDATE)

    validate = await invoke_lambda("validate_extraction", ...)

    for doc in survivors:
        result = validate.find(doc.document_index)
        if result.is_error:
            if input.persist:
                await mark_document_failed(doc.id, result.error)
            await self._checkpoint(DOCUMENT_FAILED, ...)
        else:
            if input.persist:
                await mark_document_completed(doc.id, extraction=..., validation=...)
            await self._checkpoint(DOCUMENT_COMPLETED, ...)

    # Final aggregate
    final_status = JobStatus.COMPLETED if all_ok else JobStatus.PARTIAL if some_ok else JobStatus.FAILED
    await self._checkpoint(JOB_COMPLETED if final_status != FAILED else JOB_FAILED, ...)
```

Helper `_checkpoint` (método de la clase del workflow):

```python
async def _checkpoint(
    self,
    type: CaseEventType,
    *,
    document_id: UUID | None = None,
    payload: dict,
) -> None:
    """
    1. Incrementa self._seq (estado del workflow).
    2. Construye un CaseEvent con (type, seq, ts, case_id, job_id, document_id?, payload).
    3. Si persist=True → llama update_processing_job_status (PG) con el nuevo (status, current_step, last_seq).
    4. Llama publish_event (Redis) con el CaseEvent.
    Orden estricto: PG primero, Redis después (D1).
    """
```

Notas:
- Si `persist=False`, los pasos 3 y la persistencia de `workflow_documents` son
  no-ops (el flag se evalúa dentro del helper y dentro del workflow para los
  `mark_document_*`). No duplicamos el workflow.
- Si `persist=False`, los `document_id` son UUIDs sintéticos generados en el
  workflow. Útil para correr el workflow standalone con `just start-workflow`.

### 6.6 Endpoint para iniciar el job

**Reutilizamos** el endpoint existente:

```
POST /v1/workflows/{workflow_id}/cases/{case_id}/files/{file_id}/extract
```

Hoy: `start_case_file_extraction`. Lo modificamos para:
1. Crear fila en `processing_jobs` con `status='pending'`.
2. Lanzar `DocumentProcessingWorkflow` con `persist=True`.
3. Retornar `{ job_id }` al cliente.

El job NO se considera "started" hasta que el workflow emite `JOB_STARTED`. El
endpoint solo dispara, no bloquea.

### 6.7 Endpoint SSE — refactor

Reemplazar el actual `stream_case_events` por uno basado en Redis Pub/Sub:

```
GET /v1/workflows/{workflow_id}/cases/{case_id}/events?since_seq={n}
```

Comportamiento:
1. Si `since_seq` provisto → primero replay de PG (`processing_jobs` +
   `workflow_documents` con `last_seq > since_seq`) sintetizando eventos para
   ponernos al día.
2. `SUBSCRIBE` a `case:{case_id}:events`.
3. Forward a SSE descartando eventos con `seq <= since_seq` ya replayados.

(Las eliminaciones de archivos viejos basados en pg_notify se listan
consolidadas en §6.9.)

### 6.8 Endpoint snapshot (nuevo)

```
GET /v1/workflows/{workflow_id}/cases/{case_id}/state
```

Retorna estado completo del case: jobs activos + recientes con sus
`workflow_documents` y `last_seq`. Usado por el frontend al montar la página
**antes** de abrir el SSE, para hidratar la UI sin gaps.

Ubicación: `backend/src/workflows/presentation/endpoints/case_state_endpoint.py`

### 6.9 Eliminaciones

- `case_events_endpoint.py` (actual con pg_notify) — reemplazado por el SSE de
  §6.7 sobre Redis. Archivo nuevo o renombrado, el contenido viejo se borra.
- `case_file_extract_endpoints.py::stream_job_events` — el SSE por job se
  vuelve redundante: los eventos del job ya viajan por el canal del case y el
  frontend filtra por `job_id`. Borrar el endpoint y su ruta en el router.
- `PGNotifier` para case/job events: borrar si no hay otros consumidores. Si
  se usa en otro dominio, dejarlo y solo desuscribir lo de cases/jobs.
- `_checkpoint()` viejo del `DocumentProcessingWorkflow` (la versión que
  emitía `pg_notify`) — reemplazado por el helper de §6.5.
- Suscripciones a canales `processing_jobs` / `case:*` que pasaban por PG.

## 7. Frontend — cambios

### 7.1 Hook `useCaseEvents`

Ubicación: `frontend/src/application/hooks/use-case-events.ts`

```typescript
function useCaseEvents(caseId: string) {
  // 1. Fetch snapshot
  const { data: snapshot } = useQuery(["case-state", caseId], fetchCaseState);

  // 2. Open EventSource with since_seq from snapshot
  // 3. Apply incoming events to a reducer-managed state
  // 4. Auto-reconnect with last_seq on drop

  return { jobs, documents, isConnected };
}
```

### 7.2 UI: dos niveles de cards en case detail

Ubicación: `frontend/src/presentation/workflows/cases/case-detail-view.tsx`

```
┌── Case detail ────────────────────────────────────┐
│  [+ Cargar documento]                             │
│                                                   │
│  ┌─ JobCard (file.pdf) ─────────────────────┐    │
│  │  📄 file.pdf · classifying pages 70%     │    │  ← antes de classified
│  └──────────────────────────────────────────┘    │
│                                                   │
│  ┌─ JobCard (otro.pdf) ─ classified, 2/3 done─┐  │
│  │  📄 otro.pdf · 3 documents detected        │  │
│  │   ├─ DocumentCard: Cédula     ✅ extracted │  │
│  │   ├─ DocumentCard: Póliza     ⏳ validating│  │
│  │   └─ DocumentCard: Certificado ❌ failed   │  │
│  └────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

Componentes nuevos:
- `frontend/src/presentation/workflows/cases/job-card.tsx`
- `frontend/src/presentation/workflows/cases/document-card.tsx`
- `frontend/src/presentation/workflows/cases/upload-button.tsx`

### 7.3 Botón "Cargar documento"

Flujo:
1. Selecciona archivo (input file).
2. `POST /v1/files` (existente) → `file_id`.
3. `POST /v1/workflows/{wf}/cases/{c}/files/{file_id}/extract` → `job_id`.
4. Optimistically agrega un `JobCard` en estado `pending` mientras llegan los
   primeros eventos por SSE.

## 8. Build sequence (orden sugerido)

1. **DB migration**: extender `processing_jobs` y `workflow_documents`.
2. **Enums**: `case_events.py` en `common/domain/enums/`.
3. **Domain models**:
   - Base `Event` en `common/domain/events/base.py`.
   - `CaseEvent` + payload schemas en `workflows/domain/events.py`.
4. **Infra**: `RedisEventPublisher` en `common/infrastructure/event_publisher.py`.
5. **Activities nuevas**:
   - `publish_event` en `common/infrastructure/temporal/activities/` (genérica).
   - `persist_classified_documents` y `update_processing_job_status` en
     `workflows/presentation/workflows/activities/` (específicas del dominio).
6. **Workflow refactor**: `DocumentProcessingWorkflow` con `_checkpoint` nuevo
   y flag `persist`. Registrar las nuevas activities en `run_worker.py`.
7. **Endpoint snapshot**: `GET /cases/{case_id}/state`.
8. **Endpoint SSE refactor**: reemplazar pg_notify por Redis subscribe.
9. **Eliminaciones §6.9**: borrar `stream_job_events`, viejo
   `case_events_endpoint`, `_checkpoint` con pg_notify, etc.
10. **Frontend hook**: `useCaseEvents`.
11. **Frontend UI**: `JobCard`, `DocumentCard`, `upload-button`.
12. **Integración end-to-end** + tests manuales con archivo multi-doc.

## 9. Tests

### 9.1 Backend

- Unit: cada activity (mock Redis / DB).
- Workflow test: `pytest` con `temporalio.testing.WorkflowEnvironment`,
  asserting que se emiten los eventos esperados en orden.
- Integration: subir archivo multi-doc, asegurar que el `processing_jobs` y
  `workflow_documents` quedan coherentes con los eventos publicados.
- Test específico: workflow con `persist=False` no toca DB.
- Test específico: documento que falla en `extract_fields` no aborta el resto.

### 9.2 Frontend

- Hook `useCaseEvents` con `EventSource` mockeado: snapshot + eventos en vivo +
  reconexión con `since_seq`.
- Test de reducer: aplicar secuencia de eventos produce el estado esperado.

## 10. Configuración

- `REDIS_HOST`, `REDIS_PORT`, etc. ya existen en `common/settings.py`.
- Reusar `Redis.from_url(settings.redis_url)` para el publisher (instancia
  separada del `arq_pool` ya que los pools de arq tienen settings específicos).
- Worker de Temporal (`run_worker.py`) registra las nuevas activities.

## 11. Out of scope (futuro)

- Cancelación de jobs en vuelo desde la UI.
- Reintentos manuales de un documento que falló.
- Reordenar / re-clasificar documentos manualmente desde la UI.
- Notificaciones push fuera del case detail (badge global).
- Compresión de eventos (batching) si el throughput se vuelve problema.
- Persistencia histórica de eventos (Redis Streams en vez de Pub/Sub) si
  necesitamos auditoría / replay completo más allá del estado actual.

## 12. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Cliente reconecta y pierde eventos publicados durante el gap. | Snapshot endpoint + `since_seq` reconcilia desde PG. |
| Redis se cae. | Activity `publish_event` reintenta; estado en PG nunca se pierde; al reconectar el cliente recupera vía snapshot. |
| Race entre `update_status` y `publish_event`. | Estricto: primero update PG, después publish. Snapshot siempre adelantado o igual al stream. |
| Doble publicación al replayar workflow Temporal. | Activity `update_processing_job_status` es idempotente por (`job_id`, `seq`). |
| Frontend muestra IDs que aún no existen en DB. | Imposible por D3: la activity persiste antes del checkpoint que emite `JOB_CLASSIFIED`. |

## 13. Open questions (no bloqueantes)

- ¿El `processing_jobs.last_seq` debe persistirse en cada checkpoint o solo
  al final del workflow? Recomendación: en cada checkpoint, dentro de la misma
  transacción que el cambio de status. Costo de un UPDATE extra por step es
  trivial vs el valor de tener replay confiable.
- ¿Necesitamos un endpoint para listar jobs activos del usuario a nivel
  global (badge en navbar)? Fuera de scope, pero el modelo lo soporta.
